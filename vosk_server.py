import asyncio
import os
import websockets
import json
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
import io
import subprocess

# Path to FFmpeg executable
FFMPEG_PATH = r"C:\Users\mha82\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

# Set FFmpeg path for pydub
if os.path.exists(FFMPEG_PATH):
    AudioSegment.converter = FFMPEG_PATH
else:
    print(f"Error: FFmpeg executable not found at {FFMPEG_PATH}. Please update FFMPEG_PATH in vosk_server.py.")

def convert_to_wav(audio_data, filename):
    try:
        # Determine input format based on filename extension
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in ['.mp3', '.wav']:
            return None, f"Unsupported file format: {file_extension}"

        # Load audio data using pydub
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=file_extension[1:])
        
        # Convert to WAV format suitable for Vosk (16kHz, mono, 16-bit PCM)
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        
        # Export to bytes
        output = io.BytesIO()
        audio.export(output, format="wav")
        return output.getvalue(), None
    except Exception as e:
        return None, f"Error converting audio: {str(e)}"

async def recognize(websocket, path=None):
    try:
        model_path = "D:/next_agent/vosk-model-en-us-0.42-gigaspeech"
        if not os.path.exists(model_path):
            await websocket.send(json.dumps({"error": f"Vosk model not found at {model_path}"}))
            return
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)

        while True:
            message = await websocket.recv()
            if isinstance(message, bytes):
                # Assume first message includes filename as JSON
                try:
                    config = json.loads(message)
                    if "filename" in config:
                        filename = config["filename"]
                        continue
                except json.JSONDecodeError:
                    pass

                # Convert audio to WAV format
                wav_data, error = convert_to_wav(message, filename if 'filename' in locals() else "input.wav")
                if error:
                    await websocket.send(json.dumps({"error": error}))
                    continue

                if rec.AcceptWaveform(wav_data):
                    result = json.loads(rec.Result())
                    await websocket.send(json.dumps(result))
                else:
                    partial = json.loads(rec.PartialResult())
                    await websocket.send(json.dumps(partial))
            else:
                config = json.loads(message)
                if "config" in config:
                    rec.SetMaxAlternatives(0)
                    rec.SetWords(True)
                if "eof" in config:
                    result = json.loads(rec.Result())
                    await websocket.send(json.dumps(result))
                    break
    except Exception as e:
        print(f"Error in WebSocket handler: {e}")
        await websocket.send(json.dumps({"error": str(e)}))

async def main():
    try:
        server = await websockets.serve(recognize, "localhost", 2700)
        print("Vosk WebSocket server running on ws://localhost:2700")
        await server.wait_closed()
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    asyncio.run(main())
