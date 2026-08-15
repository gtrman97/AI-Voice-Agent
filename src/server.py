"""
Step 4b: Minimal FastAPI server — proves Twilio can reach OUR server
(via ngrok) and get back dynamically generated TwiML.

No WebSocket, no OpenAI yet — just a single HTTP route.

Run: uvicorn src.server:app --reload --port 8000
(then separately: ngrok http 8000)
"""
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect

load_dotenv()

app = FastAPI()

PUBLIC_SERVER_URL = os.environ.get("PUBLIC_SERVER_URL", "")


@app.get("/")
def health_check():
    """Simple route to confirm the server is up at all, via plain browser visit."""
    return {"status": "ok", "message": "Voice bot server is running"}


@app.post("/twiml")
def twiml_webhook():
    """
    Twilio POSTs here when the call connects. This now tells Twilio to open
    a live Media Stream (raw audio WebSocket) to our /media-stream endpoint,
    instead of just reading a static script.
    """
    # Convert https:// -> wss:// for the WebSocket URL Twilio needs
    ws_url = PUBLIC_SERVER_URL.replace("https://", "wss://") + "/media-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    Twilio connects here once the call is live. It sends a stream of JSON
    messages, each wrapping a base64-encoded audio frame. For this step we
    just log what's arriving — no audio processing or AI yet.
    """
    await websocket.accept()
    frame_count = 0
    print("Media stream connected.")

    try:
        while True:
            raw_message = await websocket.receive_text()
            data = json.loads(raw_message)
            event = data.get("event")

            if event == "connected":
                print("Twilio: stream connected event received.")
            elif event == "start":
                print(f"Twilio: stream started. Stream SID: {data['start']['streamSid']}")
            elif event == "media":
                frame_count += 1
                if frame_count % 50 == 0:  # log every 50th frame, not every single one
                    print(f"Received {frame_count} audio frames so far.")
            elif event == "stop":
                print(f"Twilio: stream stopped. Total frames received: {frame_count}")

    except WebSocketDisconnect:
        print(f"Media stream disconnected. Total frames received: {frame_count}")