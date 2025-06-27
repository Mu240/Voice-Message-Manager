import asyncio
import os
import websockets
import json
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
import io
import time
import logging

# Configure logging for debugging
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


def convert_to_wav(audio_data, filename):
    """
    Convert audio data to WAV format (16kHz, mono, 16-bit PCM) for Vosk.

    Args:
        audio_data (bytes): Raw audio data.
        filename (str): Name of the audio file to determine format.

    Returns:
        tuple: (converted WAV data as bytes, error message if any).
    """
    try:
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in ['.mp3', '.wav']:
            return None, f"Unsupported file format: {file_extension}"

        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=file_extension[1:])
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        output = io.BytesIO()
        audio.export(output, format="wav")
        return output.getvalue(), None
    except Exception as e:
        logger.error(f"Error converting audio: {str(e)}")
        return None, f"Error converting audio: {str(e)}"


async def recognize(websocket, path=None):
    """
    Handle WebSocket connections, process JSON configs and audio data, and send transcription results.

    Args:
        websocket: WebSocket connection object.
        path: WebSocket path (unused).
    """
    try:
        model_path = "D:/next_agent/vosk-model-en-us-0.42-gigaspeech"
        if not os.path.exists(model_path):
            error_msg = f"Vosk model not found at {model_path}"
            logger.error(error_msg)
            await websocket.send(json.dumps({"error": error_msg}))
            return

        logger.info("Loading Vosk model...")
        start_time = time.time()
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)
        logger.info(f"Model loaded in {time.time() - start_time:.2f} seconds")

        filename = "input.wav"
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=120.0)
                logger.debug(f"Received message type: {type(message)}")

                if isinstance(message, str):
                    try:
                        config = json.loads(message)
                        logger.debug(f"Received JSON: {config}")

                        if "filename" in config:
                            filename = config["filename"]
                            await websocket.send(json.dumps({"status": f"Received filename: {filename}"}))
                        if "config" in config:
                            rec.SetMaxAlternatives(0)
                            rec.SetWords(True)
                            await websocket.send(json.dumps({"status": "Configuration applied"}))
                        if "eof" in config:
                            start_time = time.time()
                            result = json.loads(rec.Result())
                            result["status"] = "Final transcription"
                            await websocket.send(json.dumps(result))
                            logger.info(f"Sent final result: {result}, took {time.time() - start_time:.2f} seconds")
                            await asyncio.sleep(1)  # Ensure client receives final message
                            break
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON: {str(e)}"
                        logger.error(error_msg)
                        await websocket.send(json.dumps({"error": error_msg}))
                elif isinstance(message, bytes):
                    logger.debug(f"Processing audio data, size: {len(message)} bytes")
                    await websocket.send(json.dumps({"status": "Processing audio..."}))

                    start_time = time.time()
                    wav_data, error = convert_to_wav(message, filename)
                    if error:
                        await websocket.send(json.dumps({"error": error}))
                        continue

                    logger.debug(f"Audio conversion took {time.time() - start_time:.2f} seconds")

                    if rec.AcceptWaveform(wav_data):
                        result = json.loads(rec.Result())
                        await websocket.send(json.dumps(result))
                        logger.info(f"Sent final result: {result}")
                    else:
                        partial = json.loads(rec.PartialResult())
                        await websocket.send(json.dumps(partial))
                        logger.debug(f"Sent partial result: {partial}")
                else:
                    error_msg = "Unsupported message type"
                    logger.error(error_msg)
                    await websocket.send(json.dumps({"error": error_msg}))

            except asyncio.TimeoutError:
                logger.warning("Receive timeout, sending keepalive")
                await websocket.send(json.dumps({"status": "Keepalive"}))
                continue

    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"WebSocket connection closed: {e}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        try:
            await websocket.send(json.dumps({"error": str(e)}))
        except websockets.exceptions.ConnectionClosedError:
            logger.warning("Failed to send error message: connection already closed")


async def main():
    """
    Start the WebSocket server with increased ping timeout for stability.
    """
    try:
        server = await websockets.serve(
            recognize,
            "localhost",
            2700,
            ping_interval=30,
            ping_timeout=120,
            close_timeout=10
        )
        logger.info("Vosk WebSocket server running on ws://localhost:2700")
        await server.wait_closed()
    except Exception as e:
        logger.error(f"Error starting server: {e}")


if __name__ == "__main__":
    asyncio.run(main())
