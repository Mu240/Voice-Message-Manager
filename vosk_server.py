import asyncio
import os
import websockets
import json
from vosk import Model, KaldiRecognizer

# Keyword lists (same as in app.py)
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

async def recognize(websocket, path=None):
    try:
        model_path = "D:/next_agent/vosk-model-en-us-0.42-gigaspeech"
        if not os.path.exists(model_path):
            await websocket.send(json.dumps({"error": f"Vosk model not found at {model_path}"}))
            return
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000, json.dumps({
            "words": voicemail_keywords + honeypot_keywords
        }))

        while True:
            message = await websocket.recv()
            if isinstance(message, bytes):
                if rec.AcceptWaveform(message):
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