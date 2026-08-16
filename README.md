# AI Voice Agent — Pretty Good AI Engineering Challenge

An autonomous voice bot that places real phone calls to an AI phone agent and
conducts realistic, multi-turn conversations to test its behavior across a
range of scenarios (scheduling, refills, hours/insurance questions, and edge
cases).

Built for the Pretty Good AI AI Engineering Challenge. Target line used for
all test calls: **+1-805-439-8008**.

## How it works (short version)

Twilio places an outbound call and streams live call audio to a small FastAPI
server over a WebSocket. That server bridges the audio directly to OpenAI's
Realtime API (speech-to-speech), which generates the bot's spoken responses
in real time. See [`docs/architecture.md`](docs/architecture.md) for the full
reasoning behind this design and the alternatives considered.

## Setup

### 1. Prerequisites
- Python 3.9+
- A [Twilio](https://www.twilio.com) account (Pay-as-you-go, not trial — trial
  accounts inject an announcement message that breaks the call flow) with one
  voice-capable phone number
- An [OpenAI](https://platform.openai.com) account with Realtime API access
  and a funded API credit balance
- [ngrok](https://ngrok.com) (or similar) for local tunneling — a free account
  is sufficient

### 2. Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy `.env.example` to `.env` and fill in your real values:
```bash
cp .env.example .env
```
See `.env.example` for the full list of required variables (Twilio
credentials, OpenAI API key, target phone number, and your ngrok URL).

### 4. Run

You'll need three terminals running concurrently:

**Terminal 1 — the bridge server:**
```bash
uvicorn src.server:app --reload --port 8000
```

**Terminal 2 — the public tunnel:**
```bash
ngrok http 8000
```
Copy the `https://...ngrok-free.app` (or `.dev`) forwarding URL it prints,
and set it as `PUBLIC_SERVER_URL` in your `.env` file.

**Terminal 3 — place a call:**
```bash
python src/run_call.py <scenario_key>
```
Run `python src/run_call.py` with no arguments to see the full list of
available scenarios (defined in `config/scenarios.yaml`). The script waits
for the call to finish, then downloads the recording to `calls/`; the
transcript is saved automatically by the server as the call happens.

## Project structure

```
├── src/                  # Core bridge/orchestration logic — reusable, not tied to any specific business
│   ├── server.py          # FastAPI server: Twilio <-> OpenAI Realtime bridge
│   ├── run_call.py         # Main script: place a call for a given scenario, save recording + transcript
│   ├── hangup_call.py      # Utility: force-end an active call by SID
│   └── download_recording.py  # Utility: re-check/download a recording by call SID
├── config/
│   └── scenarios.yaml     # Target-specific config: personas, goals, shared fake identity
├── calls/                 # Output: recordings (.mp3) + transcripts (.json) per call
├── docs/
│   ├── architecture.md    # Design decisions and tradeoffs
│   └── bug_report.md      # Bugs found in Pretty Good AI's agent during testing
├── .env.example
└── requirements.txt
```

Configuration (`config/scenarios.yaml`) is intentionally kept separate from
core logic (`src/`) — retargeting this bot at a different business or test
scenarios means editing the YAML file only; nothing in `src/` needs to change.

## Notable design decisions

- **OpenAI Realtime API (speech-to-speech) over a cascaded STT→LLM→TTS
  pipeline** — chosen for lower latency and more natural turn-taking, which
  was the top evaluation priority for this challenge. See
  [`docs/architecture.md`](docs/architecture.md) for the full tradeoff
  analysis.
- **Audio format matching** — both Twilio and OpenAI are configured to use
  G.711 μ-law audio, Twilio's native telephony format, so no transcoding
  happens anywhere in the bridge.
- **Scenario/goal separated from core prompt behavior** — a shared
  `base_instructions` block (natural phone conversation behavior) applies to
  every call, with each scenario only adding its specific goal on top.
- **Twilio-native call recording** rather than custom audio capture, and
  **live transcript capture from Realtime API events** rather than a
  separate transcription pass — both chosen to minimize custom code for
  functionality the platforms already provide reliably.

## Known limitations

- Interruption handling clears Twilio's audio queue but does not track exact
  playback position for sample-accurate mid-word truncation.
- The bot occasionally still overlaps with the other party's opening greeting
  or produces a redundant closing turn — prompt-based instructions reduced
  but did not fully eliminate this; it appears to be non-deterministic model
  behavior rather than a fixable prompt issue. A more robust fix would
  suppress bot audio output at the code level for the first moment of the
  call, rather than relying on instructions alone.
- Scenario steering is currently a fixed persona per call; a more advanced
  version could adapt the persona's approach based on how the conversation
  unfolds in real time.

## Bug report

See [`docs/bug_report.md`](docs/bug_report.md) for issues found in Pretty
Good AI's agent during testing.