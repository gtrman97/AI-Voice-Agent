"""
Step 4b (final check): Twilio places a call and fetches its instructions
from OUR server (via ngrok), instead of static inline TwiML.

Proves the full chain: Twilio -> ngrok -> our FastAPI server -> TwiML -> back to Twilio.

Before running: make sure your ngrok URL is set in .env as PUBLIC_SERVER_URL
(e.g. PUBLIC_SERVER_URL=https://hypnotist-verse-hacking.ngrok-free.dev)

Run: python src/test_call_webhook.py
"""
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
FROM_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]
TO_NUMBER = os.environ["TARGET_PHONE_NUMBER"]
SERVER_URL = os.environ["PUBLIC_SERVER_URL"]

client = Client(ACCOUNT_SID, AUTH_TOKEN)

webhook_url = f"{SERVER_URL}/twiml"

call = client.calls.create(
    to=TO_NUMBER,
    from_=FROM_NUMBER,
    url=webhook_url,   # Twilio will POST here to fetch TwiML, instead of using inline TwiML
)

print(f"Call placed. SID: {call.sid}")
print(f"Status: {call.status}")
print(f"Twilio will fetch instructions from: {webhook_url}")