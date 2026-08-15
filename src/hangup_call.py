"""
Utility: hang up an active call by its Call SID.

Run: python src/hangup_call.py <call_sid>
"""
import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]

client = Client(ACCOUNT_SID, AUTH_TOKEN)

if len(sys.argv) != 2:
    print("Usage: python src/hangup_call.py <call_sid>")
    sys.exit(1)

call_sid = sys.argv[1]
call = client.calls(call_sid).update(status="completed")
print(f"Call {call_sid} status set to: {call.status}")