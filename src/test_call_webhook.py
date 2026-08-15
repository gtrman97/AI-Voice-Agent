"""
Step 4d verification: places a call with recording enabled, waits for the
call to finish, then downloads the recording as an MP3 so we can actually
listen to how the conversation sounded.

Run: python src/test_call_webhook.py
"""
import os
import time
import requests
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
    url=webhook_url,
    record=True,  # Twilio records the full call natively — no custom audio capture needed
)

print(f"Call placed. SID: {call.sid}")
print("Waiting for call to complete...")

# Poll call status until it's finished
while True:
    call = call.fetch()
    if call.status in ("completed", "failed", "busy", "no-answer", "canceled"):
        break
    time.sleep(3)

print(f"Call ended. Final status: {call.status}")

# Recording processing can take a few seconds after the call ends — poll until
# the recording's status is actually "completed", not just present in the list.
print("Waiting for recording to be ready...")
recording = None
for _ in range(20):
    recordings = client.recordings.list(call_sid=call.sid, limit=1)
    if recordings and recordings[0].status == "completed":
        recording = recordings[0]
        break
    elif recordings:
        print(f"Recording found but status is '{recordings[0].status}', waiting...")
    time.sleep(3)

if not recording:
    print("No recording found. The call may have been too short, or recording failed.")
else:
    os.makedirs("calls", exist_ok=True)
    mp3_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
    response = requests.get(mp3_url, auth=(ACCOUNT_SID, AUTH_TOKEN))

    filename = f"calls/{call.sid}.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)

    print(f"Recording saved to: {filename}")