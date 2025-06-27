# Voice Message Manager

A Flask and Streamlit-based application integrated with a Vosk WebSocket server and a FastAPI client for managing voicemail audio files, processing audio or text inputs to detect voicemail or honeypot keywords, and providing audio transcription capabilities. The system includes a web API for responding to inputs, a user interface for managing audio files, and a transcription service using Vosk.

## Overview

This project consists of three main Python files:
- **`app.py`**: A Flask and Streamlit application that provides a web API for handling audio/text inputs and a UI for managing voicemail audio files.
- **`vosk_server.py`**: A WebSocket server using Vosk for real-time audio transcription.
- **`client.py`**: A FastAPI-based client for transcribing audio files locally via an API endpoint.

The application detects voicemail or honeypot keywords in text or transcribed audio and serves appropriate audio responses. It supports MP3 and WAV file uploads, default audio file selection, and file deletion through a Streamlit UI.

## Features
- **API Endpoints**: Process audio or text to detect voicemail/honeypot keywords and return audio file links or transcriptions.
- **File Management**: Upload, set default, and delete MP3/WAV files via Streamlit UI.
- **Keyword Detection**: Identify voicemail and honeypot patterns in text or audio.
- **Vosk Integration**: Real-time audio transcription via WebSocket server (`vosk_server.py`) or local API (`client.py`).
- **Audio Playback**: Preview default audio files in the UI.
- **MySQL Logging**: Configurable interaction logging (disabled by default in `app.py`).

## Prerequisites
- **Python**: 3.8 or higher
- **FFmpeg**: Required for audio conversion
- **Vosk Model**: `vosk-model-en-us-0.42-gigaspeech` for speech recognition
- **MySQL**: Optional, for interaction logging
- **Dependencies**: Install via `requirements.txt`

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Mu240/Voice-Message-Manager.git
   cd Voice-Message-Manager
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   
   Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**:
   - Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html).
   - Extract and note the path to `ffmpeg.exe` (e.g., `C:\Users\<YourUser>\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe`).
   - Update the `FFMPEG_PATH` variable in both `vosk_server.py` and `client.py`:
     ```python
     FFMPEG_PATH = r"<path-to-ffmpeg.exe>"
     ```

5. **Download Vosk Model**:
   - Download `vosk-model-en-us-0.42-gigaspeech` from [Vosk models](https://alphacephei.com/vosk/models).
   - Extract to a directory (e.g., `D:/next_agent/vosk-model-en-us-0.42-gigaspeech`).
   - Update the `model_path` variable in `vosk_server.py` and `client.py`:
     ```python
     model_path = "<path-to-vosk-model>"
     ```

6. **(Optional) Configure MySQL**:
   - Set up a MySQL database and update `DB_CONFIG` in `app.py`:
     ```python
     DB_CONFIG = {
         "host": "localhost",
         "user": "<your_mysql_user>",
         "password": "<your_mysql_password>",
         "database": "<your_database_name>"
     }
     ```
   - Uncomment the `log_interaction` call in `app.py` to enable logging.

7. **Create Audio Directory**:
   - The `audio_files` directory is automatically created by `app.py` on startup.
   - Ensure write permissions in the project directory.

## File Descriptions and Usage

### 1. `app.py`
- **Purpose**: Runs a Flask server for API endpoints and a Streamlit UI for managing audio files and testing the API.
- **Functionality**:
  - **API Endpoints**:
    - `POST /api/respond`: Detects voicemail/honeypot keywords in text input and returns a response with an audio link (if voicemail detected).
    - `POST /upload`: Uploads MP3 files to the `audio_files` directory.
    - `GET /audio/file/<filename>`: Serves audio files from the `audio_files` directory.
  - **Streamlit UI**:
    - Upload MP3 files and set them as default.
    - Delete audio files.
    - Preview default audio.
    - Test the `/api/respond` endpoint with text inputs.
- **Paths to Configure**:
  - `audio_directory`: Directory for storing audio files (default: `audio_files`).
  - `selected_default_file_path`: Path to `default_audio.txt` (default: `audio_files/default_audio.txt`).
  - `DB_CONFIG`: MySQL credentials (if enabled).
- **How to Run**:
  ```bash
  streamlit run app.py
  ```
  - Access the UI at `http://localhost:8501`.
  - The Flask server runs on `http://localhost:5000`.
- **How to Test**:
  - **UI Testing**:
    - Open `http://localhost:8501` in a browser.
    - Upload an MP3 file via the "Upload a new VM audio file" section.
    - Set a default audio file using the "📌 Default" button or dropdown.
    - Delete files using the "🗑️ Delete" button.
    - Test the API using the "Test API Endpoint" form with sample text like "Please leave your message after the tone" (voicemail) or "can you hear me" (honeypot).
  - **API Testing**:
    - Send a POST request to `http://localhost:5000/api/respond`:
      ```bash
      curl -X POST http://localhost:5000/api/respond -H "Content-Type: application/json" -d '{"text": "Please leave a message", "uuid": "test-uuid", "phone_number": "1234567890"}'
      ```
      Expected response (voicemail detected):
      ```json
      {"audio_link": "http://localhost:5000/audio/file/<default_audio>.mp3", "response": "VM", "transfer": 0, "end": 1}
      ```
    - Upload an MP3 file:
      ```bash
      curl -X POST http://localhost:5000/upload -F "file=@/path/to/audio.mp3"
      ```
      Expected response:
      ```json
      {"audio_url": "http://localhost:5000/audio/file/audio.mp3"}
      ```

### 2. `vosk_server.py`
- **Purpose**: Runs a WebSocket server for real-time audio transcription using Vosk.
- **Functionality**:
  - Accepts audio data (MP3/WAV) or JSON configuration via WebSocket (`ws://localhost:2700`).
  - Converts audio to WAV (16kHz, mono, 16-bit PCM) using FFmpeg.
  - Transcribes audio using the Vosk model and sends results back to the client.
  - Supports partial and final transcription results.
- **Paths to Configure**:
  - `FFMPEG_PATH`: Path to `ffmpeg.exe`.
  - `model_path`: Path to the Vosk model directory.
- **How to Run**:
  ```bash
  python vosk_server.py
  ```
  - The server runs on `ws://localhost:2700`.

### 3. `client.py`
- **Purpose**: A FastAPI-based client for local audio transcription using Vosk.
- **Functionality**:
  - Provides a `/transcribe` endpoint to transcribe MP3/WAV files.
  - Converts audio to WAV (16kHz, mono, 16-bit PCM) using FFmpeg.
  - Returns transcription results as JSON.
- **Paths to Configure**:
  - `FFMPEG_PATH`: Path to `ffmpeg.exe`.
  - `model_path`: Path to the Vosk model directory.
- **How to Run**:
  ```bash
  python client.py
  ```
  - The server runs on `http://localhost:8000`.
- **How to Test**:
  - Send a POST request to `http://localhost:8000/transcribe`:
    ```bash
    curl -X POST http://localhost:8000/transcribe -H "Content-Type: application/json" -d '{"file_path": "/path/to/audio.mp3"}'
    ```
    Expected response (example):
    ```json
    {"result": [{"word": "hello", "start": 0.0, "end": 0.5, "conf": 0.99}], "status": "Final transcription"}
    ```
  - Ensure the audio file path is accessible to the server.

## Running the Full Application
1. **Start the Vosk WebSocket Server**:
   ```bash
   python vosk_server.py
   ```
   - Verify it’s running on `ws://localhost:2700`.
2. **Start the FastAPI Client (Optional)**:
   ```bash
   python client.py
   ```
   - Verify it’s running on `http://localhost:8000`.
3. **Start the Main Application**:
   ```bash
   streamlit run app.py
   ```
   - Access the UI at `http://localhost:8501`.
   - The Flask API runs on `http://localhost:5000`.
4. **Test the System**:
   - Upload an MP3 file via the Streamlit UI.
   - Set it as the default audio.
   - Test the `/api/respond` endpoint with voicemail text (e.g., "Please leave a message") to verify the audio link response.
   - Test the `/transcribe` endpoint (if using `client.py`) with an audio file path.
   - Use a WebSocket client to test `vosk_server.py` with audio data.

## Directory Structure
- `app.py`: Flask and Streamlit application for API and UI.
- `vosk_server.py`: Vosk WebSocket server for transcription.
- `client.py`: FastAPI client for local audio transcription.
- `audio_files/`: Directory for storing MP3/WAV files.
- `default_audio.txt`: Stores the name of the default audio file.
- `requirements.txt`: Python dependencies.

## Notes
- **File Formats**: Only MP3 and WAV files are supported for uploads and transcription.
- **MySQL Logging**: Disabled by default in `app.py`. Enable by configuring `DB_CONFIG` and uncommenting `log_interaction`.
- **Firewall**: Ensure ports `5000` (Flask), `8501` (Streamlit), `2700` (Vosk WebSocket), and `8000` (FastAPI) are open.
- **Vosk Model**: The model path must be correct in both `vosk_server.py` and `client.py`.
- **FFmpeg**: The FFmpeg path must be correct in both `vosk_server.py` and `client.py`.
- **Performance**: Loading the Vosk model may take a few seconds on startup.
- **Testing**: Use small audio files (e.g., <10MB) for faster testing.

## Troubleshooting
- **FFmpeg Not Found**: Verify the `FFMPEG_PATH` in `vosk_server.py` and `client.py`.
- **Vosk Model Not Found**: Ensure the `model_path` points to the correct directory.
- **Port Conflicts**: Check if ports `5000`, `8501`, `2700`, or `8000` are in use.
- **Audio File Issues**: Ensure uploaded files are valid MP3/WAV and not corrupted.
- **API Errors**: Check logs in the terminal for detailed error messages.
