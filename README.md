# 🎙️ AI Receptionist

AI-powered voice receptionist that books appointments via natural conversation.
Built with **LiveKit Agents** + **MCP** + **Sarvam AI** — optimised for Indian languages and clients.

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
| Tool protocol | MCP (Model Context Protocol) | Standard tool calling — add tools without changing agent |
| MCP server | FastMCP | Lightweight Python MCP server |
| STT | Sarvam saaras:v3 | Best Indian language transcription, ~₹0.50/min |
| TTS | Sarvam bulbul:v3 | Natural Indian voices, ~₹0.25/min |
| LLM | OpenAI GPT-4o-mini | Fast, cheap, reliable |
| VAD | Silero | Detects when caller speaks/stops |
| Calendar | Google Calendar API | Books appointments directly |

## Cost per minute (Indian stack)

| Component | Cost |
|-----------|------|
| Sarvam STT + TTS | ₹0.75/min |
| GPT-4o-mini | ₹0.80/min |
| LiveKit (self-hosted) | ₹0.00/min |
| **Total** | **~₹2.55/min** |

## Architecture

```
Caller speaks
    → Silero VAD detects speech
    → Sarvam STT (saaras:v3) → text
    → GPT-4o-mini decides what to do
    → MCP tool called (Google Calendar)
    → GPT-4o-mini generates reply
    → Sarvam TTS (bulbul:v3) → voice
    → Caller hears response
```

## Project Structure

```
ai-receptionist/
├── agent.py              ← Voice pipeline (LiveKit Agents)
├── server.py             ← FastAPI (creates agent rooms)
├── mcp_server.py         ← MCP server (exposes tools)
├── prompts.py            ← System prompts (dynamic date)
├── setup_google_auth.py  ← Google OAuth (run once)
├── tools/
│   ├── __init__.py
│   └── calendar.py       ← Google Calendar functions
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

### 5. Test
```bash
# Check health
curl http://localhost:8000/health

# Create an agent
curl -X POST http://localhost:8000/create-agent \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "Priya", "agent_type": "Receptionist", "voice_gender": "Female"}'
```

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Google auth (one time)
python setup_google_auth.py

# Terminal 1 — MCP tools server
python mcp_server.py

# Terminal 2 — Agent worker
python agent.py dev

# Terminal 3 — Test via mic
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
| `MCP_URL` | MCP server SSE endpoint |

## Adding New Tools

1. Add a function to `tools/calendar.py` (or create a new file in `tools/`)
2. Register it in `mcp_server.py` with `@mcp.tool()`
3. Restart the MCP server
4. Update the system prompt in `prompts.py` to mention the new tool

No changes to `agent.py` needed — MCP handles tool discovery automatically.

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
