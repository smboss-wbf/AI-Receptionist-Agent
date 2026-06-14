# AI Receptionist — Makefile
# Run `make help` to see all commands

.PHONY: help setup build up down logs dev clean auth

help:
	@echo "AI Receptionist — Voice Agent"
	@echo ""
	@echo "Commands:"
	@echo "  make setup    — First time setup (copy .env, run auth)"
	@echo "  make build    — Build Docker images"
	@echo "  make up       — Start all services"
	@echo "  make down     — Stop all services"
	@echo "  make logs     — View logs from all services"
	@echo "  make dev      — Run locally without Docker (3 terminals)"
	@echo "  make auth     — Set up Google Calendar OAuth"
	@echo "  make clean    — Remove containers and images"

setup:
	@echo "Setting up AI Receptionist..."
	@cp -n .env.example .env || true
	@echo "1. Edit .env with your API keys"
	@echo "2. Place credentials.json from Google Cloud Console in this folder"
	@echo "3. Run: make auth"
	@echo "4. Run: make up"

auth:
	@echo "Setting up Google Calendar OAuth..."
	python setup_google_auth.py

build:
	docker compose build

up:
	docker compose up -d
	@echo ""
	@echo "Services started:"
	@echo "  LiveKit:    ws://localhost:7880"
	@echo "  MCP server: http://localhost:9000/sse"
	@echo "  API server: http://localhost:8000"
	@echo "  Agent:      running and waiting for calls"

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	@echo "Starting in dev mode (3 terminals needed):"
	@echo ""
	@echo "Terminal 1: python mcp_server.py"
	@echo "Terminal 2: python agent.py dev"
	@echo "Terminal 3: uvicorn server:app --port 8000 --reload"

clean:
	docker compose down --rmi all --volumes --remove-orphans
