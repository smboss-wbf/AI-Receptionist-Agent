# 🎙️ AI Receptionist

AI-powered voice receptionist that books appointments via natural conversation.
Built with **LiveKit Agents** + **Sarvam AI** — optimised for Indian languages and clients.

## Demo

```
Caller: "Hi, I want to book a checkup"
Priya:  "Of course! May I know your name please?"
Caller: "Rahul Sharma"
Priya:  "What service do you need, Rahul?"
Caller: "Regular checkup this Monday at 10am"
Priya:  "Monday is available at 10am. Shall I confirm a 30-minute checkup?"
Caller: "Yes please"
Priya:  "Done! Your checkup is confirmed for Monday at 10am. See you then!"
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Voice pipeline | LiveKit Agents | Open source, self-hostable, no per-minute fee |
| Tools | Direct Python function tools | Reliable — avoids MCP SSE session issues on Windows |
| STT | Sarvam saaras:v3 | Best Indian language transcription, ~₹0.50/min |
| TTS | Sarvam bulbul:v3 | Natural Indian voices, ~₹0.25/min |
| LLM | OpenAI GPT-4o | Fast, reliable function-calling |
| VAD | Silero | Detects when caller speaks/stops |
| Calendar | Google Calendar API | Books appointments directly |
| Multi-client | LiveKit room metadata | Per-client prompt/voice, one worker serves all |

## Cost per minute (Indian stack)

| Component | Cost |
|-----------|------|
| Sarvam STT + TTS | ₹0.75/min |
| GPT-4o | ₹1.50/min |
| LiveKit (self-hosted) | ₹0.00/min |
| **Total** | **~₹2.25–3.50/min** |

## Architecture

```
Caller speaks
    → Silero VAD detects speech
    → Sarvam STT (saaras:v3) → text
    → GPT-4o decides what to do
    → Calendar tool called directly (no MCP, runs in ThreadPoolExecutor)
    → GPT-4o generates reply
    → Sarvam TTS (bulbul:v3) → voice
    → Caller hears response
```

## Multi-client architecture

One `agent.py` worker serves unlimited clients. Each client's config (system
prompt, voice, clinic name) lives in the LiveKit room's metadata, set at room
creation time by `server.py` (called from n8n or any HTTP client).

```
n8n / Dashboard
    → POST /create-agent  {agent_name, voice_gender, knowledge_file}
    → server.py creates a LiveKit room with metadata
    → returns room_name
    → caller joins room (via token from /get-token)
    → agent.py reads room.metadata and configures itself per-call
```

## Project Structure

```
ai-receptionist/
├── agent.py              ← Voice pipeline (LiveKit Agents)
├── server.py             ← FastAPI (creates agent rooms)
├── prompts.py             ← System prompts (dynamic date)
├── setup_google_auth.py  ← Google OAuth (run once)
├── tools/
│   ├── __init__.py
│   └── calendar.py       ← Google Calendar functions (sync + executor)
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── .env.example
```

## Quick Start (Docker)

### Prerequisites
- Docker + Docker Compose
- Google Cloud project with Calendar API enabled
- OpenAI API key
- Sarvam AI API key

### 1. Clone and setup
```bash
git clone https://github.com/YOUR_USERNAME/ai-receptionist.git
cd ai-receptionist
make setup
```

### 2. Configure environment
```bash
# Edit .env with your API keys
nano .env
```

### 3. Google Calendar OAuth (one time)
```bash
# Place credentials.json from Google Cloud Console in this folder
make auth
# Browser opens → sign in → token.json saved
```

### 4. Start everything
```bash
make build
make up
```

This starts 3 containers: `livekit`, `agent`, `server`.

### 5. Test
```bash
# Check health
curl http://localhost:8001/health

# Create an agent room
curl -X POST http://localhost:8001/create-agent \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "Priya", "agent_type": "Receptionist", "voice_gender": "Female", "knowledge_file": ""}'

# Get a caller token (use room_name from above)
curl -X POST http://localhost:8001/get-token \
  -H "Content-Type: application/json" \
  -d '{"room_name": "agent-xxxxxxxx", "participant_name": "test-caller"}'
```

Then open `https://agents-playground.livekit.io`, paste the token + LiveKit
URL, and talk to the agent.

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Google auth (one time)
python setup_google_auth.py

# Terminal 1 — Agent worker
python agent.py dev

# Terminal 2 — FastAPI server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3 — Test via mic (no server needed)
python agent.py console
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | LiveKit API key (min 32 chars) |
| `LIVEKIT_API_SECRET` | LiveKit API secret (min 32 chars) |
| `OPENAI_API_KEY` | OpenAI API key |
| `SARVAM_API_KEY` | Sarvam AI API key |

## Adding New Tools

1. Add a sync function to `tools/calendar.py` (e.g. `_cancel_appointment_sync`)
2. Add a matching `@function_tool()` async method inside the `DentalReceptionist`
   class in `agent.py`, calling it via `loop.run_in_executor(_executor, fn, ...)`
3. Restart `agent.py`
4. Update the system prompt in `prompts.py` to mention the new tool and its rules

No MCP server to manage — tools are plain Python methods on the Agent class.

## Per-client configuration (multi-tenant)

Every client gets a unique LiveKit room created via `POST /create-agent`.
The request body becomes the room's metadata, which `agent.py` reads at the
start of each call:

```json
{
  "agent_name": "Priya",
  "voice_gender": "Female",
  "knowledge_file": "You are Priya, receptionist at Sharma Dental Clinic..."
}
```

`server.py` also accepts `system_prompt` instead of `knowledge_file` (used by
the n8n "Build Prompt" node), so either field name works.

## Deployment (Hostinger VPS)

```bash
# SSH into VPS
ssh root@your-vps-ip

# Clone repo
git clone https://github.com/YOUR_USERNAME/ai-receptionist.git
cd ai-receptionist

# Setup
make setup
# Edit .env with production keys
make auth
make build
make up
```

## License

MIT
