# Voice Message Manager

A Flask and Streamlit application with Vosk WebSocket and FastAPI client for managing voicemail audio, detecting keywords, and transcribing audio. Supports MP3/WAV uploads, keyword detection, and transcription via a web API and UI.

## Features
- **API Endpoints**: Detect voicemail/honeypot keywords in text/audio; return audio links/transcriptions.
- **File Management**: Upload, set default, delete MP3/WAV files via Streamlit UI.
- **Vosk Transcription**: Real-time audio transcription via WebSocket (`vosk_server.py`) or local API (`client.py`).
- **Audio Playback**: Preview default audio in UI.
- **MySQL Logging**: Optional interaction logging.

## Prerequisites
- Python 3.8+
- FFmpeg
- Vosk model: `vosk-model-en-us-0.42-gigaspeech`
- MySQL (optional, for logging)
- Dependencies: `requirements.txt`

## Installation
1. **Clone Repository**:
   ```bash
   git clone https://github.com/Mu240/Voice-Message-Manager.git
   cd Voice-Message-Manager
   ```
2. **Set Up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Install FFmpeg**:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html).
   - Set `FFMPEG_PATH` in `vosk_server.py` and `client.py`:
     ```python
     FFMPEG_PATH = r"<path-to-ffmpeg.exe>"
     ```
5. **Download Vosk Model**:
   - Get `vosk-model-en-us-0.42-gigaspeech` from [Vosk models](https://alphacephei.com/vosk/models).
   - Set `model_path` in `vosk_server.py` and `client.py`:
     ```python
     model_path = "<path-to-vosk-model>"
     ```
6. **(Optional) MySQL**:
   - Configure `DB_CONFIG` in `app.py`:
     ```python
     DB_CONFIG = {
         "host": "localhost",
         "user": "<user>",
         "password": "<password>",
         "database": "<database>"
     }
     ```
   - Uncomment `log_interaction` to enable logging.

## File Overview and Testing

### 1. `app.py`
- **Purpose**: Flask API for keyword detection and audio file management; Streamlit UI for file uploads and API testing.
- **API Endpoints**:
  - `POST /api/respond`: Detects voicemail/honeypot keywords in text.
  - `POST /upload`: Uploads MP3/WAV files.
  - `GET /audio/file/<filename>`: Serves audio files.
- **Input Parameters**:
  - `/api/respond` (JSON):
    ```json
    {
        "text": "<input text>",
        "uuid": "<unique identifier>",
        "phone_number": "<phone number>"
    }
    ```
    - `text`: Text to analyze (e.g., "Please leave a message").
    - `uuid`: Unique ID for request (e.g., "test-uuid").
    - `phone_number`: Phone number (e.g., "1234567890").
  - `/upload` (multipart/form-data):
    - `file`: MP3/WAV file.
- **How to Test**:
  - **Run**: `streamlit run app.py`
  - **UI Testing** (`http://localhost:8501`):
    - Upload MP3/WAV via "Upload a new VM audio file".
    - Set default audio using "📌 Default" button.
    - Delete files with "🗑️ Delete" button.
    - Test `/api/respond` in "Test API Endpoint" form with text like "Please leave a message".
  - **API Testing**:
    - **Respond Endpoint**:
      ```bash
      curl -X POST http://localhost:5000/api/respond -H "Content-Type: application/json" -d '{"text": "Please leave a message", "uuid": "test-uuid", "phone_number": "1234567890"}'
      ```
      Expected: `{"audio_link": "http://localhost:5000/audio/file/<default>.mp3", "response": "VM", "transfer": 0, "end": 1}`
    - **Upload Endpoint**:
      ```bash
      curl -X POST http://localhost:5000/upload -F "file=@/path/to/audio.mp3"
      ```
      Expected: `{"audio_url": "http://localhost:5000/audio/file/audio.mp3"}`

### 2. `vosk_server.py`
- **Purpose**: Vosk WebSocket server for real-time audio transcription.
- **Input Parameters**:
  - WebSocket (`ws://localhost:2700`):
    - Audio data (MP3/WAV) or JSON config with audio metadata.
    - Example JSON config:
      ```json
      {"config": {"sample_rate": 16000}}
      ```
    - Followed by raw audio bytes.
- **How to Test**:
  - **Run**: `python vosk_server.py`
  - **Test with WebSocket Client**:
    1. Use a WebSocket client (e.g., `wscat` or Python script).
    2. Connect to `ws://localhost:2700`.
    3. Send JSON config: `{"config": {"sample_rate": 16000}}`.
    4. Send audio bytes from a 16kHz, mono, 16-bit PCM WAV file.
    5. Receive transcription results (e.g., `{"result": [{"word": "hello", "start": 0.0, "end": 0.5, "conf": 0.99}]}).
  

### 3. `client.py`
- **Purpose**: FastAPI client for local audio transcription using Vosk.
- **Input Parameters**:
  - `POST /transcribe` (JSON):
    ```json
    {
        "file_path": "<path-to-audio-file>"
    }
    ```
    - `file_path`: Path to MP3/WAV file (e.g., "C:/Users/mha82/Downloads/ttsmaker-file-2025-6-26-16-52-36.wav").
- **How to Test**:
  - **Run**: `python client.py`
  - **API Testing**:
    ```bash
    curl -X POST http://localhost:8000/transcribe -H "Content-Type: application/json" -d '{"file_path": "C:/Users/mha82/Downloads/ttsmaker-file-2025-6-26-16-52-36.wav"}'
    ```
    Expected: `{"result": [{"word": "hello", "start": 0.0, "end": 0.5, "conf": 0.99}], "status": "Final transcription"}`
  - **Verify**:
    - Ensure the file exists and is accessible.
    - Use small MP3/WAV files (<10MB) for faster testing.

## Running the Application
1. Start Vosk server: `python vosk_server.py`
2. Start FastAPI client: `python client.py`
3. Start main app: `streamlit run app.py`
4. Test via UI (`http://localhost:8501`) or API calls.

## Notes
- **Supported Formats**: MP3, WAV.
- **Ports**: Ensure `5000` (Flask), `8501` (Streamlit), `2700` (Vosk), `8000` (FastAPI) are open.
- **Troubleshooting**:
  - Verify `FFMPEG_PATH` and `model_path` in `vosk_server.py` and `client.py`.
  - Check file accessibility for transcription.
  - Monitor terminal logs for errors.
