import asyncio
import websockets
import json
import logging
import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydub import AudioSegment
import io
import time
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Vosk WebSocket Client API")

async def download_audio(url: str) -> tuple[bytes, str, str]:
    """
    Download audio file from the given URL.

    Args:
        url: URL to the audio file.

    Returns:
        Tuple of (audio data as bytes, filename, error message if any).
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            audio_data = response.content
            filename = os.path.basename(urlparse(url).path)
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension not in ['.mp3', '.wav']:
                return None, filename, f"Unsupported file format: {file_extension}"
            logger.debug(f"Downloaded audio from {url}, size: {len(audio_data)} bytes")
            return audio_data, filename, None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading audio: {e}")
        return None, "", f"HTTP error downloading audio: {str(e)}"
    except httpx.RequestError as e:
        logger.error(f"Request error downloading audio: {e}")
        return None, "", f"Request error downloading audio: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error downloading audio: {e}")
        return None, "", f"Unexpected error downloading audio: {str(e)}"

async def send_audio_to_websocket(audio_data: bytes, filename: str, config: dict = None) -> dict:
    """
    Send audio data to the WebSocket server in chunks and collect transcription results.

    Args:
        audio_data: Raw audio data as bytes.
        filename: Name of the audio file (used to determine format).
        config: Optional configuration dictionary for the recognizer.

    Returns:
        Dictionary containing concatenated transcription, errors, and status.
    """
    uri = "ws://localhost:2700"
    result = {"transcription": "", "errors": [], "status": "incomplete"}
    transcription_parts = []  # Collect all transcription parts
    try:
        async with websockets.connect(uri, ping_interval=30, ping_timeout=300, close_timeout=30, max_size=52_428_800) as websocket:
            logger.info(f"Connected to WebSocket server at {uri}")

            # Send configuration if provided
            if config:
                await websocket.send(json.dumps({"config": config}))
                logger.debug(f"Sent config: {config}")

            # Send filename
            await websocket.send(json.dumps({"filename": filename}))
            logger.debug(f"Sent filename: {filename}")

            # Send audio data in chunks
            chunk_size = 1_000_000  # 1 MB chunks
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await websocket.send(chunk)
                await websocket.send(json.dumps({"chunk": i // chunk_size + 1}))
                logger.debug(f"Sent audio chunk {i // chunk_size + 1}, size: {len(chunk)} bytes")
                await asyncio.sleep(0.1)  # Small delay to prevent overwhelming the server

            # Send EOF to signal end of audio
            await websocket.send(json.dumps({"eof": 1}))
            logger.debug("Sent EOF")

            # Receive responses
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=300.0)
                    logger.debug(f"Received message: {message}")
                    response = json.loads(message)

                    if "error" in response:
                        result["errors"].append(response["error"])
                        logger.error(f"Server error: {response['error']}")
                    elif "status" in response:
                        logger.info(f"Server status: {response['status']}")
                    elif "partial" in response:
                        transcription_parts.append(response["partial"])
                        logger.debug(f"Partial transcription: {response['partial']}")
                    elif "text" in response:
                        transcription_parts.append(response["text"])
                        logger.info(f"Final transcription: {response['text']}")
                        result["status"] = "complete"

                    # Check for final transcription
                    if response.get("status") == "Final transcription":
                        break

                except asyncio.TimeoutError:
                    logger.warning("WebSocket receive timeout")
                    result["errors"].append("WebSocket receive timeout")
                    await websocket.send(json.dumps({"status": "Keepalive"}))
                    continue
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.warning(f"WebSocket connection closed: {e}")
                    result["errors"].append(f"WebSocket connection closed: {str(e)}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    result["errors"].append(f"Invalid JSON received: {str(e)}")
                    break

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        result["errors"].append(f"WebSocket connection error: {str(e)}")
        result["status"] = "failed"

    # Concatenate all transcription parts into a single string
    result["transcription"] = " ".join(part for part in transcription_parts if part).strip()

    return result

@app.post("/transcribe")
async def transcribe_audio(request: Request):
    """
    HTTP endpoint to transcribe audio from a URL via WebSocket server.

    Args:
        request: JSON payload with `url` and optional `config`.

    Returns:
        JSON response with concatenated transcription, errors, status, and processing time.
    """
    try:
        # Parse JSON payload
        data = await request.json()
        url = data.get("url")
        config = data.get("config")

        # Validate inputs
        if not url:
            raise HTTPException(status_code=400, detail="Missing url field")

        # Download audio
        start_time = time.time()
        audio_data, filename, error = await download_audio(url)
        if error:
            raise HTTPException(status_code=400, detail=error)

        # Send to WebSocket server
        result = await send_audio_to_websocket(audio_data, filename, config)
        result["processing_time"] = time.time() - start_time

        return JSONResponse(content=result)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
