# 🎙️ AI Receptionist — Self-Hosted Telephony (Docker)

AI-powered voice receptionist that answers real phone calls and books
appointments via natural conversation. Fully self-hosted: LiveKit server,
LiveKit SIP (telephony bridge), and Redis all run in your own Docker
containers — no LiveKit Cloud, no per-minute managed SIP fees.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice pipeline | LiveKit Agents (self-hosted server) |
| Telephony bridge | LiveKit SIP (self-hosted, built from source) |
| Coordination | Redis (required by LiveKit SIP) |
| STT | Sarvam saaras:v3 |
| TTS | Sarvam bulbul:v3 |
| LLM | OpenAI GPT-4o |
| VAD | Silero |
| Calendar | Google Calendar API (OAuth, token.json) |

## Architecture

```
Phone call (SIP client or real carrier via a trunk provider)
    → livekit-sip     (translates phone audio into LiveKit's format)
    → livekit          (manages the room where caller + agent meet)
    → agent            (your AI receptionist — STT, LLM, TTS, calendar tools)
```

All five services run as Docker containers: `redis`, `livekit`,
`livekit-sip`, `agent`, `server`.

## Project Structure

```
ai-receptionist/
├── agent.py                  ← Voice pipeline (LiveKit Agents)
├── server.py                 ← FastAPI (creates agent rooms)
├── prompts.py                 ← System prompts
├── setup_google_auth.py      ← Google OAuth (run once, generates token.json)
├── setup_sip_trunk.sh        ← One-time SIP trunk + dispatch rule setup
├── livekit-config.yaml       ← livekit-server config (Redis-backed)
├── sip-config.yaml           ← livekit-sip config
├── tools/
│   ├── __init__.py
│   └── calendar.py           ← Google Calendar functions (token.json based)
├── Dockerfile                ← Builds the agent/server Python image
├── Dockerfile.sip            ← Builds livekit-sip from source
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── .env.example
```

## Quick Start (Docker — Windows, Mac, or Linux)

### Prerequisites
- Docker Desktop installed and running
- A Google Cloud project with Calendar API enabled and an OAuth Client ID
  (Desktop app type) downloaded as `credentials.json`
- OpenAI API key
- Sarvam AI API key
- The `lk` CLI installed on your host machine (not in Docker) — needed once
  for the SIP trunk setup step. See https://github.com/livekit/livekit-cli

### 1. Clone and configure
```bash
git clone <your-repo-url>
cd ai-receptionist
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and SARVAM_API_KEY
```

### 2. Google Calendar OAuth (one time, run locally — NOT in Docker)
```bash
pip install google-auth-oauthlib google-api-python-client
python setup_google_auth.py
```
This opens a browser, asks you to sign in, and creates `token.json` in this
folder. Docker Compose mounts this file into the `agent` and `server`
containers automatically.

### 3. Build and start everything
```bash
docker compose build
docker compose up -d
```

This starts 5 containers: `redis`, `livekit`, `livekit-sip`, `agent`,
`server`. Check they're all running:
```bash
docker compose ps
```

### 4. Create the SIP trunk and dispatch rule (one time)
```bash
chmod +x setup_sip_trunk.sh
./setup_sip_trunk.sh
```
This requires the `lk` CLI on your host (talking to the dockerized
`livekit-server` on `localhost:7880`). It creates:
- An inbound SIP trunk (currently open to any address — restrict this in
  production to your real SIP provider's IP range)
- A dispatch rule that creates a fresh room per caller and assigns the
  `dental-receptionist` agent to it

Verify:
```bash
lk sip dispatch list
```
The `Agents` column should show `dental-receptionist`.

### 5. Test with a SIP softphone

Since there's no real phone number connected yet, use a SIP test client to
simulate an inbound call. On Windows, **MicroSIP** is a good free option
(similar role to `pjsua`/`baresip` used during Mac validation):

1. Download and install [MicroSIP](https://www.microsip.org/)
2. Skip/avoid creating any SIP account — you want a direct call, not
   registration (the trunk has no authentication configured)
3. Dial directly to: `sip:1234@localhost:5060` (or your Docker host's LAN
   IP if `localhost` doesn't resolve correctly from MicroSIP)

You should hear the AI receptionist greet you. Check logs if not:
```bash
docker compose logs -f livekit-sip
docker compose logs -f agent
```

## What's different from the previous (non-Docker) local Mac setup

The Mac validation used locally-installed binaries (`livekit-server`,
`livekit-sip` built from source, Redis via Homebrew) across multiple
terminal tabs. This Docker setup containerizes the exact same architecture
so it runs identically on Windows, Linux, or Mac — `Dockerfile.sip` builds
`livekit-sip` from source inside its container the same way it was built
manually before, with the same native dependencies (`libopus`, `libsoxr`,
`libopusfile`).

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | Points at the dockerized livekit-server (`ws://livekit:7880` from inside Docker) |
| `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | Must match the `keys:` section in `livekit-config.yaml` and `sip-config.yaml` exactly |
| `OPENAI_API_KEY` | OpenAI API key |
| `SARVAM_API_KEY` | Sarvam AI API key |

## Adding New Tools

1. Add a sync function to `tools/calendar.py`
2. Add a matching `@function_tool()` async method inside the
   `DentalReceptionist` class in `agent.py`, calling it via
   `loop.run_in_executor(_executor, fn, ...)`
3. Rebuild and restart: `docker compose up -d --build agent`
4. Update the system prompt in `prompts.py` to mention the new tool

## Connecting a real phone number (Plivo)

This setup is validated with simulated SIP calls only. Here's the actual,
confirmed path to connect a real phone number via Plivo.

**Prerequisite:** the server must already be publicly reachable (deployed
to a VPS, not running on a laptop) — Plivo cannot route calls to a private
IP like `192.168.1.x`. Do the VPS deployment (see below) before this.

### 1. Buy a number and create a Plivo inbound trunk
1. Sign up at [plivo.com](https://www.plivo.com), add balance
2. Go to **Phone Numbers → Buy Number**, pick an Indian number
3. Go to **Zentrunk → Inbound Trunks → Create New Inbound Trunk**
4. **India requirement:** if handling calls to/from India, your LiveKit
   region must be set to India — this is a regulatory requirement, not
   optional, calls will fail without it

### 2. Point the Plivo trunk at this server
In the trunk's destination/primary URI field, enter your server's public
IP and port:
```
<your-server-public-ip>:5060;transport=tcp
```

### 3. Attach the number to the trunk
Go to **Phone Numbers → Your Numbers**, select your number, set
**Application Type** to **Zentrunk**, and choose the trunk created above.

### 4. Lock down the LiveKit-side trunk to Plivo's real IPs
The trunk created by `setup_sip_trunk.sh` is wide open (`0.0.0.0/0`) for
local testing only. Once a real number is live, restrict it to Plivo's
actual signaling IPs. Confirm which region serves your number in the Plivo
console, then update accordingly:

| Region | Signaling IP range |
|---|---|
| Singapore (closest to India) | `18.136.1.128/26` |
| North California, USA | `13.52.9.0/25`, `216.120.187.128/26` |
| Virginia, USA | `18.214.109.128/25`, `18.215.142.0/26`, `204.89.148.128/26` |
| Frankfurt, Germany | `3.120.121.128/26` |
| São Paulo, Brazil | `18.228.70.64/26` |
| Sydney, Australia | `13.238.202.192/26` |

```bash
cat > /tmp/sip-inbound-trunk-update.json << 'EOF'
{
  "name": "Plivo Production Trunk",
  "allowedAddresses": ["18.136.1.128/26"]
}
EOF

lk sip inbound update --id <your-trunk-id> /tmp/sip-inbound-trunk-update.json
```

### 5. Ports
Plivo signals on port **5060** (UDP/TCP) and sends media on ports
**10000–30000** (UDP/TCP). `livekit-config.yaml` and `docker-compose.yml`
in this project are already set to this range — confirm your VPS firewall
opens both 5060 and 10000–30000 as well.

### 6. Deploy to a VPS instead of a laptop
1. Copy this whole project folder to your VPS (e.g. Hostinger)
2. In `livekit-config.yaml`, set `use_external_ip: true`
3. Run `docker compose build && docker compose up -d` on the VPS
4. Re-run `setup_sip_trunk.sh` (or the trunk update above) against the
   VPS's `livekit-server`
5. Open ports 5060 and 10000–30000 in the VPS firewall

### 7. Test it
Call your new Plivo number from any phone. It should ring through to the
AI receptionist exactly like the local softphone tests did.

## License

MIT