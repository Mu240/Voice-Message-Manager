import uuid
from flask import Flask, request, jsonify, send_from_directory
import os
import streamlit as st
import threading
import pymysql
from datetime import datetime
import requests
import time

app = Flask(__name__)

# Static audio file path
audio_directory = "audio_files"
selected_default_file_path = os.path.join(audio_directory, "default_audio.txt")
os.makedirs(audio_directory, exist_ok=True)

# Function to get the default audio file from default_audio.txt
def get_default_audio_file():
    if os.path.exists(selected_default_file_path):
        with open(selected_default_file_path, "r") as f:
            default_audio = f.read().strip()
        # Verify the file exists in audio_directory
        if os.path.exists(os.path.join(audio_directory, default_audio)):
            return default_audio
    return None

# MySQL configuration (disabled for now)
DB_CONFIG = {
    "host": "localhost",
    "user": "your_user",
    "password": "your_password",
    "database": "voicemail_db"
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def log_interaction(user_uuid, phone_number, text, response, transfer, end):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO interactions (uuid, phone_number, text, response, transfer, end, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (user_uuid, phone_number, text,
                                 response, transfer, end, datetime.now()))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging interaction: {e}")

def contains_keywords(text, keyword_list):
    if not text:
        return False
    lowered = text.lower()
    # Check if any keyword or a close variation (substring) is present
    for keyword in keyword_list:
        keyword_lower = keyword.lower()
        # Split keyword into words and check if any significant word is in the text
        keyword_words = keyword_lower.split()
        for word in keyword_words:
            if len(word) > 3 and word in lowered:  # Only match words longer than 3 chars to avoid noise
                return True
        # Also check if the full keyword is a substring
        if keyword_lower in lowered:
            return True
    return False

# Keyword lists
voicemail_keywords = [
    "After the beep",
    "Please leave a message",
    "At the tone",
    "After the tone",
    "Please leave your message",
    "Please record a message",
    "Please record your message",
    "Voice messaging system",
    "Unable to answer the phone right now",
    "Person you are trying to reach is not available"
]
honeypot_keywords = [
    "im listening",
    "i dont hear you",
    "please explain",
    "why are you calling",
    "say your name",
    "i did not consent",
    "otherwise",
    "date and time",
    "consent",
    "please say your name",
    "please fully describe your product or service",
    "describe",
    "product or service",
    "product",
    "service",
    "can you hear me",
    "what did you say",
    "location",
    "company",
    "located",
    "email",
    "are you there",
    "tell me more",
    "wait wait wait",
    "can you hear me good good good",
    "go ahead and",
    "go ahead and do it",
    "blessed day",
    "call me back later"
]

@app.route("/api/respond", methods=["POST"])
def respond():
    data = request.json or {}
    text = data.get("text", "")
    user_uuid = data.get("uuid", str(uuid.uuid4()))
    phone_number = data.get("phone_number", "")

    # Get the current default audio file dynamically
    default_audio_file = get_default_audio_file()

    if contains_keywords(text, voicemail_keywords):
        audio_link = f"http://localhost:5000/audio/file/{default_audio_file}" if default_audio_file else ""
        response_data = {
            "audio_link": audio_link,
            "response": "VM",
            "transfer": 0,
            "end": 1
        }
    elif contains_keywords(text, honeypot_keywords):
        response_data = {
            "audio_link": "",
            "response": "No VM",
            "transfer": 0,
            "end": 1
        }
    else:
        response_data = {
            "audio_link": "",
            "response": "continue",
            "transfer": 0,
            "end": 1
        }

    # log_interaction(user_uuid, phone_number, text, response_data["response"], response_data["transfer"], response_data["end"])  # Disabled temporarily
    return jsonify(response_data)

@app.route("/audio/file/<filename>")
def get_audio_file(filename):
    try:
        return send_from_directory(audio_directory, filename)
    except FileNotFoundError:
        return jsonify({"error": f"File {filename} not found"}), 404

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if file and file.filename.endswith('.mp3'):
        file_path = os.path.join(audio_directory, file.filename)
        file.save(file_path)
        return jsonify({"audio_url": f"http://localhost:5000/audio/file/{file.filename}"}), 200
    return jsonify({"error": "Invalid file format, only MP3 allowed"}), 400

# Streamlit UI
if __name__ == "__main__":
    # Initialize Flask server only once using session state
    if 'flask_started' not in st.session_state:
        def run_flask():
            app.run(debug=False, port=5000, use_reloader=False)

        threading.Thread(target=run_flask, daemon=True).start()
        st.session_state.flask_started = True
        time.sleep(1)  # Give Flask time to start

    st.title("Voice Message Manager & API Tester")

    # Initialize session state for managing refreshes
    if 'refresh_trigger' not in st.session_state:
        st.session_state.refresh_trigger = 0

    # Initialize file list in session state to avoid unnecessary refreshes
    if 'last_file_count' not in st.session_state:
        st.session_state.last_file_count = 0

    uploaded_file = st.file_uploader("Upload a new VM audio file", type=["mp3"])
    if uploaded_file and uploaded_file.name not in st.session_state.get('processed_files', set()):
        # Initialize processed files set if not exists
        if 'processed_files' not in st.session_state:
            st.session_state.processed_files = set()

        file_path = os.path.join(audio_directory, uploaded_file.name)
        try:
            # Save file locally first
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            # Upload to server
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), 'audio/mpeg')}
            response = requests.post("http://localhost:5000/upload", files=files)

            if response.status_code == 200:
                # Automatically set the uploaded file as default
                with open(selected_default_file_path, "w") as f:
                    f.write(uploaded_file.name)

                # Mark file as processed to prevent re-processing
                st.session_state.processed_files.add(uploaded_file.name)

                st.success(f"✅ Uploaded and set {uploaded_file.name} as the new default VM audio.")

                # Use st.experimental_rerun() or just let the next run handle the refresh
                time.sleep(0.3)
                st.rerun()
            else:
                st.warning(f"⚠️ Saved locally but failed to upload to server: {response.text}")
        except Exception as e:
            st.error(f"❌ Error processing upload: {str(e)}")

    st.subheader("Available Voice Files")

    # Get available audio files with error handling
    try:
        audio_files = []
        if os.path.exists(audio_directory):
            audio_files = [f for f in os.listdir(audio_directory)
                           if f.endswith(".mp3") and os.path.exists(os.path.join(audio_directory, f))]
        else:
            os.makedirs(audio_directory, exist_ok=True)
    except Exception as e:
        st.error(f"Error reading audio directory: {e}")
        audio_files = []

    # Handle file deletion
    if 'delete_requested' in st.session_state and st.session_state.delete_requested:
        file_to_delete = st.session_state.delete_file
        try:
            file_path = os.path.join(audio_directory, file_to_delete)

            # Check if file exists before attempting deletion
            if os.path.exists(file_path):
                # Check if this is the current default before deletion
                current_default = get_default_audio_file()
                is_default = (current_default == file_to_delete)

                # Delete the file
                os.remove(file_path)

                # If deleted file was default, clear default_audio.txt
                if is_default and os.path.exists(selected_default_file_path):
                    os.remove(selected_default_file_path)
                    st.warning(f"⚠️ Deleted default file {file_to_delete}. Please select a new default.")
                else:
                    st.success(f"✅ Deleted {file_to_delete}")

                # Remove from processed files if it exists
                if 'processed_files' in st.session_state and file_to_delete in st.session_state.processed_files:
                    st.session_state.processed_files.remove(file_to_delete)
            else:
                st.error(f"❌ File {file_to_delete} not found!")

        except FileNotFoundError:
            st.error(f"❌ File {file_to_delete} was already deleted or not found!")
        except Exception as e:
            st.error(f"❌ Error deleting {file_to_delete}: {e}")
        finally:
            # Clear the delete request
            if 'delete_requested' in st.session_state:
                del st.session_state.delete_requested
            if 'delete_file' in st.session_state:
                del st.session_state.delete_file
            # Force immediate rerun after deletion to refresh the file list
            st.rerun()

    files_to_delete = []
    for audio_file in audio_files:
        col1, col2, col3 = st.columns([3, 1, 1])

        # Get current default to show indicator
        current_default = get_default_audio_file()
        file_display_name = f"🎵 {audio_file}"
        if current_default == audio_file:
            file_display_name = f"⭐ {audio_file} (Default)"

        with col1:
            st.write(file_display_name)

        with col2:
            # Set as default button
            if st.button(f"📌 Default", key=f"default_{audio_file}", disabled=(current_default == audio_file)):
                try:
                    with open(selected_default_file_path, "w") as f:
                        f.write(audio_file)
                    st.success(f"✅ Set {audio_file} as default!")
                    # No need for immediate rerun, let natural refresh handle it
                except Exception as e:
                    st.error(f"❌ Failed to set default: {e}")

        with col3:
            # Delete button - only show if file actually exists
            if os.path.exists(os.path.join(audio_directory, audio_file)):
                if st.button(f"🗑️ Delete", key=f"delete_{audio_file}"):
                    # Set deletion request in session state instead of immediate deletion
                    st.session_state.delete_requested = True
                    st.session_state.delete_file = audio_file
                    st.rerun()
            else:
                st.write("❌ Missing")

    # Show current default audio player
    if audio_files:
        current_default = get_default_audio_file()
        if current_default and current_default in audio_files:
            # Double-check the file exists before trying to play it
            audio_path = os.path.join(audio_directory, current_default)
            if os.path.exists(audio_path):
                st.subheader("Current Default Audio")
                try:
                    st.audio(audio_path, format='audio/mp3')
                    st.info(f"🎵 Currently playing: {current_default}")
                except Exception as e:
                    st.warning(f"⚠️ Cannot play default audio: {str(e)}")
            else:
                st.warning(f"⚠️ Default file {current_default} not found! Please select a new default.")
                # Clear the invalid default
                if os.path.exists(selected_default_file_path):
                    os.remove(selected_default_file_path)
        else:
            st.info("ℹ️ No default audio file set. Click '📌 Default' next to any file to set it as default.")
    else:
        st.info("ℹ️ No audio files available. Please upload an MP3 file.")

    # Simplified default selection (alternative method)
    if audio_files:
        st.subheader("Alternative: Select Default via Dropdown")
        current_default = get_default_audio_file()

        # Filter current_default to ensure it exists in the current file list
        if current_default and current_default not in audio_files:
            current_default = None
            # Clear invalid default
            if os.path.exists(selected_default_file_path):
                os.remove(selected_default_file_path)

        try:
            current_index = audio_files.index(current_default) if current_default in audio_files else 0
        except (ValueError, IndexError):
            current_index = 0

        selected_audio = st.selectbox(
            "Choose Default Audio File",
            audio_files,
            index=current_index,
            key="default_selector"
        )

        if st.button("Set Selected as Default", key="set_selected_default"):
            try:
                # Verify the selected file still exists
                if os.path.exists(os.path.join(audio_directory, selected_audio)):
                    with open(selected_default_file_path, "w") as f:
                        f.write(selected_audio)
                    st.success(f"✅ Set {selected_audio} as the new default VM audio.")
                else:
                    st.error(f"❌ Selected file {selected_audio} no longer exists!")
            except Exception as e:
                st.error(f"❌ Failed to set default audio file: {e}")

    st.subheader("Test API Endpoint")
    with st.form("test_form"):
        test_uuid = st.text_input("UUID", str(uuid.uuid4()))
        test_phone = st.text_input("Phone Number", "1234567890")
        test_text = st.text_area("Text", "Please leave your message after the tone")
        submitted = st.form_submit_button("Send Test")

        if submitted:
            try:
                response = requests.post("http://localhost:5000/api/respond", json={
                    "uuid": test_uuid,
                    "phone_number": test_phone,
                    "text": test_text
                })
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ API Response:")
                    st.json(result)

                    # Show additional info about the response
                    if result.get("response") == "VM":
                        st.info("🎵 Voicemail keywords detected - VM audio will be played")
                    elif result.get("response") == "No VM":
                        st.info("🚫 Honeypot keywords detected - No VM audio included")
                    else:
                        st.info("➡️ AI VM detected - continue")

                else:
                    st.error(f"❌ Failed to call API: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"❌ Failed to call API: {str(e)}")

    # Show current status
    st.sidebar.subheader("Current Status")
    current_default = get_default_audio_file()
    if current_default:
        st.sidebar.success(f"✅ Default Audio: {current_default}")
    else:
        st.sidebar.warning("⚠️ No default audio set")

    st.sidebar.info(f"📁 Total Files: {len(audio_files)}")
    if audio_files:
        st.sidebar.write("**Available Files:**")
        for file in audio_files:
            if file == current_default:
                st.sidebar.write(f"⭐ {file}")
            else:
                st.sidebar.write(f"🎵 {file}")
