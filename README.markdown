# Voice Message Manager

A Flask and Streamlit application integrated with a Vosk WebSocket server and FastAPI client for managing voicemail audio, detecting keywords, and transcribing audio. Supports MP3/WAV uploads, keyword detection, and transcription via a web API and UI.

## Features
- **API Endpoints**: Detect voicemail/honeypot keywords in text and serve audio files (`app.py`); transcribe audio via WebSocket (`vosk_server.py`, `client.py`).
- **File Management**: Upload, set default, and delete MP3/WAV files via Streamlit UI (`app.py`).
- **Vosk Transcription**: Real-time audio transcription using Vosk WebSocket server (`vosk_server.py`) and FastAPI client (`client.py`).
- **Audio Playback**: Preview default audio in Streamlit UI (`app.py`).
- **MySQL Logging**: Optional interaction logging (disabled in `app.py`).

## Prerequisites
- **Python**: 3.8+
- **FFmpeg**: Required for audio conversion.
- **Vosk Model**: `vosk-model-en-us-0.42-gigaspeech` for transcription.
- **MySQL**: Optional, for logging interactions.
- **Dependencies**: Listed in `requirements.txt`.

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
   - Update `FFMPEG_PATH` in `client.py` and `vosk_server.py`:
     ```python
     FFMPEG_PATH = r"<path-to-ffmpeg.exe>"  # e.g., r"C:\ffmpeg\bin\ffmpeg.exe"
     ```
5. **Download Vosk Model**:
   - Get `vosk-model-en-us-0.42-gigaspeech` from [Vosk models](https://alphacephei.com/vosk/models).
   - Update `model_path` in `vosk_server.py`:
     ```python
     model_path = "<path-to-vosk-model>"  # e.g., "D:/vosk-model-en-us-0.42-gigaspeech"
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
   - Uncomment `log_interaction` call in `app.py` to enable logging.

## File Overview and Testing

### 1. `app.py`
- **Purpose**: Flask API for keyword detection and audio file management; Streamlit UI for file uploads, management, and API testing.
- **API Endpoints**:
  - `POST /api/respond`: Detects voicemail/honeypot keywords in text and returns audio link or status.
    - **Input** (JSON):
      ```json
      {
          "text": "<input text>",
          "uuid": "<unique identifier>",
          "phone_number": "<phone number>"
      }
      ```
      - `text`: Text to analyze (e.g., "Please leave a message").
      - `uuid`: Unique ID (e.g., "test-uuid").
      - `phone_number`: Phone number (e.g., "1234567890").
    - **Output**: JSON with `audio_link`, `response` ("VM", "No VM", or "not available"), `transfer`, `end`.
  - `POST /upload`: Uploads MP3 files to `audio_files` directory.
    - **Input**: Multipart form-data with `file` (MP3).
    - **Output**: JSON with `audio_url`.
  - `GET /audio/file/<filename>`: Serves audio files from `audio_files` directory.
- **How to Test**:
  - **Run**: `streamlit run app.py`
  - **UI Testing** (`http://localhost:8501`):
    - Upload MP3 via "Upload a new VM audio file".
    - Set default audio using "📌 Default" or dropdown.
    - Delete files with "🗑️ Delete".
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
- **Purpose**: WebSocket server for real-time audio transcription using Vosk.
- **Input Parameters**:
  - WebSocket (`ws://localhost:2700`):
    - JSON config (e.g., `{"config": {"sample_rate": 16000}}`, `{"filename": "audio.mp3"}`, `{"eof": 1}`).
    - Raw audio bytes (MP3/WAV).
  - **Output**: JSON with transcription (`partial`, `text`, or `error`), status, or keepalive messages.
- **How to Test**:
  - **Run**: `python vosk_server.py`  
  - **Verify**:
    - Check logs for model loading and transcription results.
    - Ensure Vosk model path and FFmpeg path are correct.

### 3. `client.py`
- **Purpose**: FastAPI client to download audio from a URL, send it to the Vosk WebSocket server, and return transcriptions.
- **Input Parameters**:
  - `POST /transcribe` (JSON):
    ```json
    {
        "url": "<audio-url>",
        "config": {"sample_rate": 16000}  // optional
    }
    ```
    - `url`: URL to MP3/WAV file (e.g., "http://localhost:5000/audio/file/audio.mp3").
    - `config`: Optional Vosk recognizer config.
  - **Output**: JSON with `transcription` (concatenated text), `errors`, `status`, `processing_time`.
- **How to Test**:
  - **Run**: `python client.py`
  - **API Testing**:
    ```bash
    curl -X POST http://localhost:8000/transcribe -H "Content-Type: application/json" -d '{"url": "http://localhost:5000/audio/file/audio.mp3"}'
    ```
    Expected: `{"transcription": "<transcribed text>", "errors": [], "status": "complete", "processing_time": <seconds>}`
  - **Verify**:
    - Ensure `vosk_server.py` is running (`ws://localhost:2700`).
    - Use small MP3/WAV files (<10MB) for faster testing.
    - Check logs for download and WebSocket communication errors.

## Running the Application
1. Start Vosk server: `python vosk_server.py`
2. Start FastAPI client: `python client.py`
3. Start main app: `streamlit run app.py`
4. Access UI at `http://localhost:8501` or test APIs via `curl`.

## Notes
- **Supported Formats**: MP3, WAV.
- **Ports**:
  - Flask: `5000`
  - Streamlit: `8501`
  - Vosk WebSocket: `2700`
  - FastAPI: `8000`
- **Troubleshooting**:
  - Verify `FFMPEG_PATH` in `client.py` and `vosk_server.py`.
  - Ensure Vosk model path is correct in `vosk_server.py`.
  - Check file accessibility for uploads and transcription.
  - Monitor logs for errors (e.g., FFmpeg or model loading issues).
  - Ensure ports are not blocked by other applications.
- **Limitations**:
  - Large audio files may cause timeouts; chunking is implemented in `client.py` to mitigate.
  - MySQL logging is disabled by default; enable carefully with proper `DB_CONFIG`.

