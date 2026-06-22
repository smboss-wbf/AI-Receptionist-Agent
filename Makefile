.PHONY: setup auth build up down logs restart clean sip-setup

# First-time setup — copies .env.example to .env if missing
setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env — edit it with your API keys"; else echo ".env already exists"; fi
	@if [ ! -f token.json ]; then echo "⚠️  Run 'make auth' first to generate token.json before 'make up'"; fi

# Run Google Calendar OAuth flow (one time, outside Docker, opens a browser)
auth:
	python setup_google_auth.py

# Build all Docker images (agent, server, and livekit-sip from source)
build:
	docker compose build

# Start all 5 services: redis, livekit, livekit-sip, agent, server
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Tail logs from all services
logs:
	docker compose logs -f

# Restart everything
restart:
	docker compose restart

# Stop and remove containers, networks, volumes
clean:
	docker compose down -v

# One-time: create the SIP inbound trunk + dispatch rule
# Run this AFTER 'make up' — requires the lk CLI installed on your host
sip-setup:
	./setup_sip_trunk.sh
