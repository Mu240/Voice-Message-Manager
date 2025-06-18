# Voice Message Manager

A Flask and Streamlit-based application for managing voicemail audio files and processing incoming text to detect voicemail or honeypot keywords. The app provides a web API for responding to text inputs and a user interface for uploading, managing, and testing voicemail audio files.

## Features
- **API Endpoint**: Processes text input to detect voicemail or honeypot keywords and returns appropriate audio file links.
- **File Management**: Upload, set default, and delete MP3 audio files via a Streamlit UI.
- **Keyword Detection**: Identifies voicemail and honeypot patterns in text to determine response actions.
- **MySQL Logging**: Configured to log interactions (currently disabled in code).
- **Audio Playback**: Play and test default audio files directly in the UI.

## Prerequisites
- Python 3.8+
- MySQL (optional, for interaction logging)
- Required Python packages (install via `requirements.txt`)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Mu240/Voice-Message-Manager.git
   cd Voice-Message-Manager
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Configure MySQL in the code by updating `DB_CONFIG` with your credentials.
5. Create an `audio_files` directory for storing MP3 files (automatically created on first run).

## Usage
1. Run the application:
   ```bash
   streamlit run app.py
   ```
2. Access the Streamlit UI at `http://localhost:8501` (default Streamlit port).
3. Use the UI to:
   - Upload MP3 files.
   - Set a default voicemail audio file.
   - Delete existing audio files.
   - Test the API with sample inputs.
4. Access the Flask API at `http://localhost:5000`:
   - **POST `/api/respond`**: Send JSON with `text`, `uuid`, and `phone_number` to get a response.
   - **POST `/upload`**: Upload an MP3 file.
   - **GET `/audio/file/<filename>`**: Retrieve an audio file.

## API Endpoints
- **POST `/api/respond`**:
  - Input: `{ "text": "string", "uuid": "string", "phone_number": "string" }`
  - Output: `{ "audio_link": "string", "response": "VM|No VM|continue", "transfer": 0|1, "end": 0|1 }`
- **POST `/upload`**:
  - Input: Form-data with `file` (MP3 file)
  - Output: `{ "audio_url": "string" }` or error message
- **GET `/audio/file/<filename>`**:
  - Output: MP3 file or 404 if not found

## Directory Structure
- `app.py`: Main application code.
- `audio_files/`: Directory for storing MP3 files.
- `default_audio.txt`: Stores the name of the default audio file.
- `.gitignore`: Ignores virtual environment, cache, and sensitive files.
- `requirements.txt`: Lists Python dependencies.

## Notes
- The MySQL logging feature is currently disabled in the code. Enable it by uncommenting the `log_interaction` call and configuring `DB_CONFIG`.
- Ensure the Flask server (`port 5000`) and Streamlit server (`port 8501`) are not blocked by your firewall.
- Only MP3 files are supported for uploads.
- The application uses a file-based approach for default audio selection (`default_audio.txt`).
