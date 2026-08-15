"""
Step 4a: Bare-bones Twilio outbound call test.

Purpose: verify Twilio credentials + outbound calling work at all,
completely isolated from OpenAI/WebSocket complexity. If this fails,
the problem is definitely on the Twilio/account side, not our bridge code.

Run: python src/test_call.py
"""
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
FROM_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]
TO_NUMBER = os.environ["TARGET_PHONE_NUMBER"]

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Static TwiML served inline (via Twilio's <Say>) — no server of ours needed yet.
# This just proves we can place a call and Twilio will speak something.
TEST_TWIML = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">This is a test call from an automated voice bot under development. Goodbye.</Say>
</Response>"""

call = client.calls.create(
    to=TO_NUMBER,
    from_=FROM_NUMBER,
    twiml=TEST_TWIML,
)

print(f"Call placed. SID: {call.sid}")
print(f"Status: {call.status}")
print(f"Calling FROM {FROM_NUMBER} TO {TO_NUMBER}")