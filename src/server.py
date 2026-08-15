"""
Step 4b: Minimal FastAPI server — proves Twilio can reach OUR server
(via ngrok) and get back dynamically generated TwiML.

No WebSocket, no OpenAI yet — just a single HTTP route.

Run: uvicorn src.server:app --reload --port 8000
(then separately: ngrok http 8000)
"""
import json
import os
import base64
import asyncio
import yaml
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect

load_dotenv()

app = FastAPI()

PUBLIC_SERVER_URL = os.environ.get("PUBLIC_SERVER_URL", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1"
VOICE = "alloy"  # known-good with Twilio's G.711 stream; avoid fable/onyx/nova (documented compatibility bug)

# Which scenario to run — for now a fixed default; the orchestration script
# will make this selectable per-call once we build it.
ACTIVE_SCENARIO = "hours_inquiry"


def load_system_prompt(scenario_key: str) -> str:
    """Combine the shared base conversational behavior with a specific
    scenario's goal, loaded from config/scenarios.yaml."""
    with open("config/scenarios.yaml") as f:
        config = yaml.safe_load(f)

    base = config["base_instructions"]
    scenario = config["scenarios"][scenario_key]
    return f"{base}\n\nYour specific goal for this call:\n{scenario['goal']}"


SYSTEM_PROMPT = load_system_prompt(ACTIVE_SCENARIO)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Voice bot server is running"}


@app.post("/twiml")
def twiml_webhook():
    ws_url = PUBLIC_SERVER_URL.replace("https://", "wss://") + "/media-stream"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


async def send_session_update(openai_ws):
    """Configure the OpenAI Realtime session to match Twilio's native audio
    format (G.711 u-law, 8kHz) on both input and output — this is what lets
    us relay audio directly with no transcoding step anywhere in the bridge."""
    session_update = {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": "gpt-realtime-2.1",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": {
                        "type": "server_vad",
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                    },
                    "transcription": {"model": "whisper-1"},
                },
                "output": {
                    "format": {"type": "audio/pcmu"},
                    "voice": VOICE,
                },
            },
            "instructions": SYSTEM_PROMPT,
        },
    }
    await openai_ws.send(json.dumps(session_update))


@app.websocket("/media-stream")
async def media_stream(twilio_ws: WebSocket):
    """
    Bridges audio between Twilio's Media Stream and OpenAI's Realtime API.
    Two concurrent tasks run for the life of the call:
      - twilio_to_openai: relays caller audio frames to OpenAI
      - openai_to_twilio: relays generated speech back to Twilio, and
        handles basic interruption (if the other party starts talking
        while our bot is still speaking, stop our audio immediately)
    """
    await twilio_ws.accept()
    print("Media stream connected.")

    stream_sid = None
    call_sid = None
    transcript = []

    async with websockets.connect(
        REALTIME_URL,
        extra_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
    ) as openai_ws:

        await send_session_update(openai_ws)

        async def twilio_to_openai():
            nonlocal stream_sid, call_sid
            try:
                async for message in twilio_ws.iter_text():
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "start":
                        stream_sid = data["start"]["streamSid"]
                        call_sid = data["start"]["callSid"]
                        print(f"Stream started. SID: {stream_sid}, Call SID: {call_sid}")

                    elif event == "media":
                        # Forward the caller's audio straight to OpenAI —
                        # already in the matching g711 ulaw format, no conversion needed.
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data["media"]["payload"],
                        }))

                    elif event == "stop":
                        print("Twilio stream stopped.")
                        break

            except WebSocketDisconnect:
                print("Twilio WebSocket disconnected.")
            finally:
                # Explicitly close our end of the OpenAI connection so nothing
                # lingers as an open background task after the call ends.
                await openai_ws.close()

        response_in_progress = False

        async def openai_to_twilio():
            nonlocal response_in_progress
            audio_chunks_sent = 0
            try:
                async for message in openai_ws:
                    data = json.loads(message)
                    event_type = data.get("type")

                    if event_type == "response.created":
                        response_in_progress = True

                    elif event_type == "response.done":
                        response_in_progress = False
                        print(f"Response finished. Audio chunks sent to Twilio: {audio_chunks_sent}")
                        audio_chunks_sent = 0

                    elif event_type == "response.output_audio.delta" and stream_sid:
                        audio_chunks_sent += 1
                        # Relay generated speech straight back to Twilio, same format, no conversion.
                        await twilio_ws.send_text(json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": data["delta"]},
                        }))

                    elif event_type == "input_audio_buffer.speech_started":
                        # OpenAI's server already auto-cancels any in-progress response
                        # when it detects new speech — we don't need to (and shouldn't)
                        # send response.cancel ourselves. We're only responsible for
                        # telling Twilio to stop playing whatever's already queued,
                        # since that's on our side of the bridge, not the server's.
                        if response_in_progress:
                            print("Interruption detected — clearing Twilio's audio queue.")
                            response_in_progress = False
                            if stream_sid:
                                await twilio_ws.send_text(json.dumps({
                                    "event": "clear",
                                    "streamSid": stream_sid,
                                }))

                    elif event_type == "response.output_audio_transcript.done":
                        # What OUR bot said
                        transcript.append({"speaker": "bot", "text": data["transcript"]})

                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # What the business's agent (the other party) said
                        transcript.append({"speaker": "agent", "text": data["transcript"]})

                    elif event_type == "error":
                        print(f"OpenAI error: {data}")

            except websockets.exceptions.ConnectionClosed:
                print("OpenAI WebSocket closed.")

        await asyncio.gather(twilio_to_openai(), openai_to_twilio())

    # Save the transcript once the call is fully finished
    if call_sid and transcript:
        os.makedirs("calls", exist_ok=True)
        transcript_path = f"calls/{call_sid}_transcript.json"
        with open(transcript_path, "w") as f:
            json.dump(transcript, f, indent=2)
        print(f"Transcript saved to: {transcript_path}")

    print("Media stream handler finished.")