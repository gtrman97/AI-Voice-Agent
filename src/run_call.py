"""
Main orchestration script: places a call for a specific scenario, waits for
it to complete, and downloads the recording. The transcript is saved
automatically by server.py as the call happens.

Usage: python src/run_call.py <scenario_key>
Example: python src/run_call.py schedule_appointment

Run without an argument to see the list of available scenarios.
"""
import os
import sys
import time
import yaml
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


def list_scenarios():
    with open("config/scenarios.yaml") as f:
        config = yaml.safe_load(f)
    print("Available scenarios:")
    for key, scenario in config["scenarios"].items():
        print(f"  {key} — {scenario['name']}")


if len(sys.argv) != 2:
    print("Usage: python src/run_call.py <scenario_key>\n")
    list_scenarios()
    sys.exit(1)

scenario_key = sys.argv[1]

# Validate the scenario exists before spending a real call on a typo
with open("config/scenarios.yaml") as f:
    config = yaml.safe_load(f)
if scenario_key not in config["scenarios"]:
    print(f"Unknown scenario: '{scenario_key}'\n")
    list_scenarios()
    sys.exit(1)

webhook_url = f"{SERVER_URL}/twiml?scenario={scenario_key}"

print(f"Placing call for scenario: {scenario_key} ({config['scenarios'][scenario_key]['name']})")

call = client.calls.create(
    to=TO_NUMBER,
    from_=FROM_NUMBER,
    url=webhook_url,
    record=True,
)

print(f"Call placed. SID: {call.sid}")
print("Waiting for call to complete...")

while True:
    call = call.fetch()
    if call.status in ("completed", "failed", "busy", "no-answer", "canceled"):
        break
    time.sleep(3)

print(f"Call ended. Final status: {call.status}, duration: {call.duration}s")

print("Waiting for recording to be ready...")
recording = None
for _ in range(20):
    recordings = client.recordings.list(call_sid=call.sid, limit=1)
    if recordings and recordings[0].status == "completed":
        recording = recordings[0]
        break
    time.sleep(3)

if not recording:
    print("No recording found or it never finished processing.")
else:
    os.makedirs("calls", exist_ok=True)
    mp3_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
    response = requests.get(mp3_url, auth=(ACCOUNT_SID, AUTH_TOKEN))

    filename = f"calls/{call.sid}_{scenario_key}.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)

    print(f"Recording saved to: {filename}")

print(f"Transcript (saved separately by the server) should be at: calls/{call.sid}_{scenario_key}_transcript.json")