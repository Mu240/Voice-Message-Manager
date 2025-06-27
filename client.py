import asyncio
import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
import io
import time
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to FFmpeg executable
FFMPEG_PATH = r"C:\Users\mha82\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

# Set FFmpeg path for pydub
if os.path.exists(FFMPEG_PATH):
    AudioSegment.converter = FFMPEG_PATH
else:
    logger.error(f"FFmpeg executable not found at {FFMPEG_PATH}. Please update FFMPEG_PATH.")
    exit(1)

# FastAPI app
app = FastAPI()


# Pydantic model for request body
class AudioRequest(BaseModel):
    file_path: str  # File path or HTTP URL to audio file (required)


def convert_to_wav(audio_data: bytes, filename: str) -> tuple[bytes | None, str | None]:
    """
    Convert audio data to WAV format (16kHz, mono, 16-bit PCM) for Vosk.

    Args:
        audio_data: Raw audio data (bytes).
        filename: Name of the audio file to determine format.

    Returns:
        tuple: (converted WAV data as bytes, error message if any).
    """
    try:
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in ['.mp3', '.wav']:
            return None, f"Unsupported file format: {file_extension}. Only .mp3 and .wav are supported."

        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=file_extension[1:])
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        output = io.BytesIO()
        audio.export(output, format="wav")
        return output.getvalue(), None
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        return None, f"Error converting audio: {str(e)}"


async def transcribe_audio(audio_data: bytes, filename: str) -> dict:
    """
    Transcribe audio data using Vosk.

    Args:
        audio_data: Raw audio data (bytes).
        filename: Name for format detection.

    Returns:
        dict: Transcription result with status and text.
    """
    model_path = "D:/next_agent/vosk-model-en-us-0.42-gigaspeech"
    if not os.path.exists(model_path):
        logger.error(f"Vosk model not found at {model_path}")
        return {"error": f"Vosk model not found at {model_path}"}

    logger.info("Loading Vosk model...")
    start_time = time.time()
    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    logger.info(f"Model loaded in {time.time() - start_time:.2f} seconds")

    logger.debug(f"Processing audio data, size: {len(audio_data)} bytes")
    wav_data, error = convert_to_wav(audio_data, filename)
    if error:
        return {"error": error}

    logger.debug(f"Audio conversion took {time.time() - start_time:.2f} seconds")

    if rec.AcceptWaveform(wav_data):
        result = json.loads(rec.Result())
        result["status"] = "Final transcription"
        logger.info(f"Transcription result: {result}")
        return result
    else:
        partial = json.loads(rec.PartialResult())
        logger.debug(f"Partial transcription: {partial}")
        return partial


@app.post("/transcribe")
async def transcribe(request: AudioRequest):
    """
    API endpoint to transcribe audio from a file path or HTTP URL.

    Args:
        request: AudioRequest with file_path (local path or HTTP URL).

    Returns:
        JSON response with transcription or error.
    """
    try:
        file_path = request.file_path
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")

        # Check if file_path is a URL
        is_url = file_path.startswith(('http://', 'https://'))

        # Derive filename
        if is_url:
            filename = os.path.basename(urlparse(file_path).path)
        else:
            filename = os.path.basename(file_path)

        # Validate file extension
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in ['.mp3', '.wav']:
            raise HTTPException(status_code=400,
                                detail=f"Unsupported file format: {file_extension}. Only .mp3 and .wav are supported.")

        # Read audio data
        if is_url:
            logger.debug(f"Downloading audio from URL: {file_path}")
            response = requests.get(file_path, timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Failed to download audio from {file_path}")
            audio_data = response.content
        else:
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Audio file not found at {file_path}")
            with open(file_path, "rb") as f:
                audio_data = f.read()

        result = await transcribe_audio(audio_data, filename)
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading audio from URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading audio: {str(e)}")
    except Exception as e:
        logger.error(f"Error in /transcribe: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
