"""
Utility: check status of and download a specific recording by its Recording SID,
without placing a new call. Useful for verifying recording downloads work.

Run: python src/download_recording.py <call_sid>
"""
import os
import sys
import requests
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]

client = Client(ACCOUNT_SID, AUTH_TOKEN)

if len(sys.argv) != 2:
    print("Usage: python src/download_recording.py <call_sid>")
    sys.exit(1)

call_sid = sys.argv[1]
recordings = client.recordings.list(call_sid=call_sid, limit=1)

if not recordings:
    print("No recording found for this call SID.")
    sys.exit(1)

recording = recordings[0]
print(f"Recording SID: {recording.sid}")
print(f"Status: {recording.status}")

if recording.status != "completed":
    print("Recording isn't ready yet — try again in a moment.")
    sys.exit(0)

os.makedirs("calls", exist_ok=True)
mp3_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
response = requests.get(mp3_url, auth=(ACCOUNT_SID, AUTH_TOKEN))

filename = f"calls/{call_sid}.mp3"
with open(filename, "wb") as f:
    f.write(response.content)

print(f"Recording saved to: {filename}")