# Voice Message Manager

A Flask and Streamlit-based application integrated with a Vosk WebSocket server for managing voicemail audio files and processing audio or text inputs to detect voicemail or honeypot keywords. The app provides a web API for responding to inputs and a user interface for uploading, managing, and testing voicemail audio files.

## Features
- **API Endpoint**: Processes audio or text input to detect voicemail or honeypot keywords and returns appropriate audio file links.
- **File Management**: Upload, set default, and delete MP3 or WAV audio files via a Streamlit UI.
- **Keyword Detection**: Identifies voicemail and honeypot patterns in transcribed audio or text to determine response actions.
- **MySQL Logging**: Configured to log interactions (currently disabled in code).
- **Audio Playback**: Play and test default audio files directly in the UI.
- **Vosk Integration**: Uses a WebSocket server with the Vosk speech recognition model for audio transcription.

## Prerequisites
- Python 3.8+
- MySQL (optional, for interaction logging)
- FFmpeg (required for audio conversion, configure path in `app.py`)
- Vosk speech recognition model (`vosk-model-en-us-0.42-gigaspeech`, configure path in `vosk_server.py`)
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
4. Download and install FFmpeg:
   - Download from [FFmpeg official site](https://ffmpeg.org/download.html).
   - Update `FFMPEG_PATH` in `app.py` with the path to `ffmpeg.exe`.
5. Download the Vosk model:
   - Download `vosk-model-en-us-0.42-gigaspeech` from [Vosk models](https://alphacephei.com/vosk/models).
   - Update `model_path` in `vosk_server.py` to point to the model directory.
6. (Optional) Configure MySQL in `app.py` by updating `DB_CONFIG` with your credentials.
7. Create an `audio_files` directory for storing MP3/WAV files (automatically created on first run).

## Usage
1. Start the Vosk WebSocket server:
   ```bash
   python vosk_server.py
   ```
   - Ensure the server is running on `ws://localhost:2700` (default).
2. Run the main application:
   ```bash
   streamlit run app.py
   ```
3. Access the Streamlit UI at `http://localhost:8501` (default Streamlit port) to:
   - Upload MP3 or WAV files.
   - Set a default voicemail audio file.
   - Delete existing audio files.
   - Test the API with sample audio or text inputs.
4. Access the Flask API at `http://localhost:5000`:
   - **POST `/api/respond`**: Send JSON with `text`, `uuid`, `phone_number`, or an audio file to get a response.
   - **POST `/upload`**: Upload an MP3 or WAV file.
   - **GET `/audio/file/<filename>`**: Retrieve an audio file.

## API Endpoints
- **POST `/api/respond`**:
  - Input: Form-data with `audio` (MP3/WAV file) or JSON with `text`, `uuid`, `phone_number`
  - Output: `{ "audio_link": "string", "response": "VM|No VM|not available", "transfer": 0|1, "end": 0|1 }`
- **POST `/upload`**:
  - Input: Form-data with `file` (MP3 or WAV file)
  - Output: `{ "audio_url": "string" }` or error message
- **GET `/audio/file/<filename>`**:
  - Output: MP3/WAV file or 404 if not found

## Directory Structure
- `app.py`: Main Flask and Streamlit application code, handling API and UI.
- `vosk_server.py`: Vosk WebSocket server for audio transcription.
- `audio_files/`: Directory for storing MP3 and WAV files.
- `default_audio.txt`: Stores the name of the default audio file.
- `.gitignore`: Ignores virtual environment, cache, and sensitive files.
- `requirements.txt`: Lists Python dependencies.

## Notes
- The MySQL logging feature is disabled by default. Enable it by uncommenting the `log_interaction` call in `app.py` and configuring `DB_CONFIG`.
- Ensure the Vosk WebSocket server (`ws://localhost:2700`), Flask server (`http://localhost:5000`), and Streamlit server (`http://localhost:8501`) are not blocked by your firewall.
- Only MP3 and WAV files are supported for uploads.
- The application uses a file-based approach for default audio selection (`default_audio.txt`).
- Audio files are converted to mono, 16kHz, 16-bit format for Vosk compatibility.
- Ensure the Vosk model path in `vosk_server.py` and FFmpeg path in `app.py` are correctly configured.
