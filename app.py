import uuid
import json
from flask import Flask, request, jsonify, send_from_directory
import os
import streamlit as st
import threading
import pymysql
from datetime import datetime
import requests
import time
import websocket
import wave
from io import BytesIO
from pydub import AudioSegment

app = Flask(__name__)

# Static audio file path
audio_directory = "audio_files"
selected_default_file_path = os.path.join(audio_directory, "default_audio.txt")
os.makedirs(audio_directory, exist_ok=True)

# Vosk WebSocket server configuration
VOSK_WS_URL = "ws://localhost:2700"

# FFmpeg configuration
FFMPEG_PATH = r"C:\Users\mha82\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"  # Path to ffmpeg.exe

# Set FFmpeg path for pydub
if os.path.exists(FFMPEG_PATH):
    AudioSegment.converter = FFMPEG_PATH
else:
    print(f"Error: FFmpeg executable not found at {FFMPEG_PATH}. Please update FFMPEG_PATH in app.py.")


# Function to convert audio (MP3 or WAV) to WAV format suitable for Vosk
def convert_to_wav(audio_data, filename):
    try:
        if not os.path.exists(FFMPEG_PATH):
            raise FileNotFoundError(f"FFmpeg executable not found at {FFMPEG_PATH}")

        extension = os.path.splitext(filename)[1].lower()
        wav_io = BytesIO()

        if extension == '.mp3':
            audio = AudioSegment.from_mp3(BytesIO(audio_data))
        elif extension == '.wav':
            audio = AudioSegment.from_wav(BytesIO(audio_data))
        else:
            raise ValueError(f"Unsupported file extension: {extension}")

        # Convert to Vosk-compatible format (mono, 16kHz, 16-bit)
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        audio.export(wav_io, format="wav")
        return wav_io.getvalue()
    except FileNotFoundError as e:
        print(
            f"Error: FFmpeg is not installed or not found at {FFMPEG_PATH}. Please verify the path or install FFmpeg.")
        return None
    except Exception as e:
        print(f"Error converting audio to WAV: {e}")
        return None


# WebSocket client to send audio to Vosk server and get text
def transcribe_audio(audio_data, filename):
    try:
        ws = websocket.create_connection(VOSK_WS_URL, timeout=10)
        extension = os.path.splitext(filename)[1].lower()

        # If WAV, check if it already meets Vosk requirements
        if extension == '.wav':
            try:
                with wave.open(BytesIO(audio_data), 'rb') as wf:
                    if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == 16000:
                        wav_data = audio_data  # Use directly if format is correct
                    else:
                        wav_data = convert_to_wav(audio_data, filename)  # Convert if format doesn't match
            except Exception as e:
                print(f"Error reading WAV file: {e}")
                wav_data = convert_to_wav(audio_data, filename)  # Fallback to conversion
        else:
            wav_data = convert_to_wav(audio_data, filename)

        if not wav_data:
            ws.close()
            return "Error: Failed to convert audio to WAV format"

        with wave.open(BytesIO(wav_data), 'rb') as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                print(
                    "Warning: Audio format may not be compatible with Vosk (mono, 16-bit, 16kHz). Attempting to process anyway.")

            ws.send(json.dumps({"config": {"sample_rate": 16000}}))
            chunk_size = 8000
            while True:
                data = wf.readframes(chunk_size)
                if len(data) == 0:
                    break
                ws.send_binary(data)

            ws.send(json.dumps({"eof": 1}))
            result = ""
            timeout_counter = 0
            max_timeout = 10

            while timeout_counter < max_timeout:
                try:
                    response = ws.recv()
                    response_json = json.loads(response)
                    if "text" in response_json and response_json["text"]:
                        result = response_json["text"]
                        break
                    elif "partial" in response_json:
                        continue
                    else:
                        break
                except websocket.WebSocketTimeoutException:
                    timeout_counter += 1
                    time.sleep(1)
                    continue

            ws.close()
            return result if result else "No transcription available"

    except websocket.WebSocketConnectionClosedException:
        print("Error: WebSocket connection closed unexpectedly")
        return "Error: WebSocket connection closed"
    except websocket.WebSocketException as e:
        print(f"Error: WebSocket error: {str(e)}")
        return f"Error: {str(e)}"
    except ConnectionRefusedError:
        print("Error: Could not connect to Vosk server - is it running on ws://localhost:2700?")
        return "Error: Could not connect to Vosk server"
    except Exception as e:
        print(f"Error in WebSocket transcription: {e}")
        return f"Error: {str(e)}"


# Function to get the default audio file
def get_default_audio_file():
    if os.path.exists(selected_default_file_path):
        with open(selected_default_file_path, "r") as f:
            default_audio = f.read().strip()
        if os.path.exists(os.path.join(audio_directory, default_audio)):
            return default_audio
    return None


# MySQL configuration (disabled by default)
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
            cursor.execute(sql, (user_uuid, phone_number, text, response, transfer, end, datetime.now()))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging interaction: {e}")


# Keyword lists
voicemail_keywords = [
    "beep", "tone", "message", "unable", "available", "system",
    "after the beep", "please leave a message", "at the tone",
    "after the tone", "please leave your message",
    "please record a message", "please record your message",
    "voice messaging system", "unable to answer the phone right now",
    "person you are trying to reach is not available"
]
honeypot_keywords = [
    "im listening", "i dont hear you", "please explain",
    "why are you calling", "say your name", "i did not consent",
    "otherwise", "date and time", "consent", "please say your name",
    "please fully describe your product or service", "describe",
    "product or service", "product", "service", "can you hear me",
    "what did you say", "location", "company", "located", "email",
    "are you there", "tell me more", "wait wait wait",
    "can you hear me good good good", "go ahead and",
    "go ahead and do it", "blessed day", "call me back later"
]


@app.route("/api/respond", methods=["POST"])
def respond():
    audio_data = request.files.get("audio") if request.files else None
    data = {}

    if request.is_json:
        data = request.json or {}
    elif request.form:
        data = request.form.to_dict()
    else:
        return jsonify({"error": "Invalid request: No JSON or form data provided"}), 400

    user_uuid = data.get("uuid", str(uuid.uuid4()))
    phone_number = data.get("phone_number", "")
    text_input = data.get("text", "")

    text = ""
    if audio_data:
        audio_content = audio_data.read()
        text = transcribe_audio(audio_content, audio_data.filename)
        if text.startswith("Error"):
            return jsonify({"error": text}), 400

    text = text if text else text_input
    default_audio_file = get_default_audio_file()

    text_lower = text.lower() if text else ""
    is_voicemail = False
    is_honeypot = False

    for keyword in voicemail_keywords:
        if keyword.lower() in text_lower:
            is_voicemail = True
            break

    if not is_voicemail:
        for keyword in honeypot_keywords:
            if keyword.lower() in text_lower:
                is_honeypot = True
                break

    if is_voicemail:
        audio_link = f"http://localhost:5000/audio/file/{default_audio_file}" if default_audio_file else ""
        response_data = {
            "audio_link": audio_link,
            "response": "VM",
            "transfer": 0,
            "end": 1
        }
    elif is_honeypot:
        response_data = {
            "audio_link": "",
            "response": "No VM",
            "transfer": 0,
            "end": 1
        }
    else:
        response_data = {
            "audio_link": "",
            "response": "not available",
            "transfer": 0,
            "end": 1
        }

    # Uncomment to enable MySQL logging
    # log_interaction(user_uuid, phone_number, text, response_data["response"], response_data["transfer"], response_data["end"])
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
    if file and file.filename.lower().endswith(('.mp3', '.wav')):
        file_path = os.path.join(audio_directory, file.filename)
        file.save(file_path)
        return jsonify({"audio_url": f"http://localhost:5000/audio/file/{file.filename}"}), 200
    return jsonify({"error": "Invalid file format, only MP3 and WAV allowed"}), 400


# Streamlit UI
if __name__ == "__main__":
    if 'flask_started' not in st.session_state:
        def run_flask():
            app.run(debug=False, port=5000, use_reloader=False)


        threading.Thread(target=run_flask, daemon=True).start()
        st.session_state.flask_started = True
        time.sleep(2)

    st.title("Voice Message Manager & API Tester")

    if 'refresh_trigger' not in st.session_state:
        st.session_state.refresh_trigger = 0

    if 'last_file_count' not in st.session_state:
        st.session_state.last_file_count = 0

    uploaded_file = st.file_uploader("Upload a new VM audio file", type=["mp3", "wav"])
    if uploaded_file and uploaded_file.name not in st.session_state.get('processed_files', set()):
        if 'processed_files' not in st.session_state:
            st.session_state.processed_files = set()

        file_path = os.path.join(audio_directory, uploaded_file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            mime_type = 'audio/mpeg' if uploaded_file.name.lower().endswith('.mp3') else 'audio/wav'
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), mime_type)}
            response = requests.post("http://localhost:5000/upload", files=files)

            if response.status_code == 200:
                with open(selected_default_file_path, "w") as f:
                    f.write(uploaded_file.name)
                st.session_state.processed_files.add(uploaded_file.name)
                st.success(f"✅ Uploaded and set {uploaded_file.name} as the new default VM audio.")
                time.sleep(0.3)
                st.rerun()
            else:
                st.warning(f"⚠️ Saved locally but failed to upload to server: {response.text}")
        except Exception as e:
            st.error(f"❌ Error processing upload: {str(e)}")

    st.subheader("Available Voice Files")

    try:
        audio_files = [f for f in os.listdir(audio_directory) if
                       f.lower().endswith((".mp3", ".wav")) and os.path.exists(os.path.join(audio_directory, f))]
    except Exception as e:
        st.error(f"Error reading audio directory: {e}")
        audio_files = []

    if 'delete_requested' in st.session_state and st.session_state.delete_requested:
        file_to_delete = st.session_state.delete_file
        try:
            file_path = os.path.join(audio_directory, file_to_delete)
            if os.path.exists(file_path):
                current_default = get_default_audio_file()
                is_default = (current_default == file_to_delete)
                os.remove(file_path)
                if is_default and os.path.exists(selected_default_file_path):
                    os.remove(selected_default_file_path)
                    st.warning(f"⚠️ Deleted default file {file_to_delete}. Please select a new default.")
                else:
                    st.success(f"✅ Deleted {file_to_delete}")
                if 'processed_files' in st.session_state and file_to_delete in st.session_state.processed_files:
                    st.session_state.processed_files.remove(file_to_delete)
            else:
                st.error(f"❌ File {file_to_delete} not found!")
        except FileNotFoundError:
            st.error(f"❌ File {file_to_delete} was already deleted or not found!")
        except Exception as e:
            st.error(f"❌ Error deleting {file_to_delete}: {e}")
        finally:
            if 'delete_requested' in st.session_state:
                del st.session_state.delete_requested
            if 'delete_file' in st.session_state:
                del st.session_state.delete_file
            st.rerun()

    for audio_file in audio_files:
        col1, col2, col3 = st.columns([3, 1, 1])
        current_default = get_default_audio_file()
        file_display_name = f"🎵 {audio_file}"
        if current_default == audio_file:
            file_display_name = f"⭐ {audio_file} (Default)"

        with col1:
            st.write(file_display_name)

        with col2:
            if st.button(f"📌 Default", key=f"default_{audio_file}", disabled=(current_default == audio_file)):
                try:
                    with open(selected_default_file_path, "w") as f:
                        f.write(audio_file)
                    st.success(f"✅ Set {audio_file} as default!")
                except Exception as e:
                    st.error(f"❌ Failed to set default: {e}")

        with col3:
            if os.path.exists(os.path.join(audio_directory, audio_file)):
                if st.button(f"🗑️ Delete", key=f"delete_{audio_file}"):
                    st.session_state.delete_requested = True
                    st.session_state.delete_file = audio_file
                    st.rerun()
            else:
                st.write("❌ Missing")

    if audio_files:
        current_default = get_default_audio_file()
        if current_default and current_default in audio_files:
            audio_path = os.path.join(audio_directory, current_default)
            if os.path.exists(audio_path):
                st.subheader("Current Default Audio")
                try:
                    audio_format = 'audio/mp3' if current_default.lower().endswith('.mp3') else 'audio/wav'
                    st.audio(audio_path, format=audio_format)
                    st.info(f"🎵 Currently playing: {current_default}")
                except Exception as e:
                    st.warning(f"⚠️ Cannot play default audio: {str(e)}")
            else:
                st.warning(f"⚠️ Default file {current_default} not found! Please select a new default.")
                if os.path.exists(selected_default_file_path):
                    os.remove(selected_default_file_path)
        else:
            st.info("ℹ️ No default audio file set. Click '📌 Default' next to any file to set it as default.")
    else:
        st.info("ℹ️ No audio files available. Please upload an MP3 or WAV file.")

    if audio_files:
        st.subheader("Alternative: Select Default via Dropdown")
        current_default = get_default_audio_file()
        if current_default and current_default not in audio_files:
            current_default = None
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
        test_audio = st.file_uploader("Upload Audio for Transcription", type=["mp3", "wav"], key="test_audio")
        submitted = st.form_submit_button("Send Test")

        if submitted:
            try:
                files = {}
                data = {
                    "uuid": test_uuid,
                    "phone_number": test_phone,
                    "text": test_text
                }
                if test_audio:
                    mime_type = 'audio/mpeg' if test_audio.name.lower().endswith('.mp3') else 'audio/wav'
                    files = {"audio": (test_audio.name, test_audio.getvalue(), mime_type)}
                response = requests.post("http://localhost:5000/api/respond", data=data, files=files)
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ API Response:")
                    st.json(result)

                    if result.get("response") == "VM":
                        st.info("🎵 Voicemail keywords detected - VM audio will be played")
                    elif result.get("response") == "No VM":
                        st.info("🚫 Honeypot keywords detected - No VM audio included")
                    else:
                        st.info("➡️ No matching keywords detected - not available")
                else:
                    st.error(f"❌ Failed to call API: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"❌ Failed to call API: {str(e)}")

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
