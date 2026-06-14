"""
Server — FastAPI server that creates voice agent rooms.

This replaces what n8n was doing visually:
    - Receives agent config (form data from WeBuildFlows)
    - Builds system prompt from knowledge file
    - Creates a LiveKit room with metadata
    - Returns agent_id back to caller

Run this alongside agent.py and mcp_server.py:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from livekit import api

from prompts import DENTAL_CLINIC_PROMPT

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="WeBuildFlows Voice Agent Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LIVEKIT_URL    = os.getenv("LIVEKIT_URL")
LIVEKIT_KEY    = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_SECRET = os.getenv("LIVEKIT_API_SECRET")
MCP_URL        = os.getenv("MCP_URL", "http://localhost:9000/sse")


# ─── Request model ────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    """
    What WeBuildFlows sends when a user fills the form.
    Each field maps to a form input on the site.
    """
    agent_name:     str                    # e.g. "Priya"
    agent_type:     str  = "Receptionist" # Receptionist, Sales, Support, Custom
    voice_gender:   str  = "Female"       # Female or Male
    knowledge_file: str  = ""             # Pasted knowledge base / instructions
    mcp_url:        str  = ""             # Which MCP server to use for tools
    # WeBuildFlows tracking fields
    user_id:        str  = ""
    run_id:         str  = ""
    callback_url:   str  = ""


# ─── Helper: map gender to Sarvam speaker ────────────────────────────────────

SPEAKER_MAP = {
    "Female": "priya",
    "Male":   "rahul",
}

# ─── Helper: build system prompt ─────────────────────────────────────────────

def build_system_prompt(request: AgentRequest) -> str:
    """
    Build the system prompt from the agent config.
    This is what the n8n Build Prompt Code node was doing.

    If the user pasted their own knowledge file — use it directly.
    If not — fall back to the demo dental clinic prompt.
    """
    if request.knowledge_file.strip():
        # User provided their own instructions — use as-is
        return request.knowledge_file.strip()

    # No knowledge file — use default dental demo prompt
    return DENTAL_CLINIC_PROMPT


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.post("/create-agent")
async def create_agent(request: AgentRequest):
    """
    Create a voice agent for a client.

    Steps:
    1. Map voice gender to Sarvam speaker name
    2. Build system prompt from knowledge file
    3. Create a LiveKit room with all config in metadata
    4. Return room name (agent_id) to WeBuildFlows

    The LiveKit room name = agent_id.
    When a caller joins this room, agent.py picks it up
    and reads the metadata to configure itself.
    """
    try:
        # Step 1 — map voice to speaker
        speaker = SPEAKER_MAP.get(request.voice_gender, "priya")

        # Step 2 — build system prompt
        system_prompt = build_system_prompt(request)

        # Step 3 — determine MCP URL
        mcp_url = request.mcp_url or MCP_URL

        # Step 4 — create unique room name
        room_name = f"agent-{uuid.uuid4().hex[:8]}"

        # Step 5 — create LiveKit room with metadata
        # agent.py reads this metadata when a caller joins
        metadata = json.dumps({
            "system_prompt": system_prompt,
            "speaker":       speaker,
            "mcp_url":       mcp_url,
            "agent_type":    request.agent_type,
            "agent_name":    request.agent_name,
            "user_id":       request.user_id,
        })

        lk = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_KEY,
            api_secret=LIVEKIT_SECRET,
        )

        await lk.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                metadata=metadata,
                empty_timeout=86400,  # room expires after 24hrs if unused
            )
        )

        await lk.aclose()

        logger.info(f"Created room {room_name} for agent '{request.agent_name}'")

        return {
            "status":     "success",
            "agent_id":   room_name,
            "agent_name": request.agent_name,
            "agent_type": request.agent_type,
            "speaker":    speaker,
            "mcp_url":    mcp_url,
            "message":    f"Agent '{request.agent_name}' is live and ready.",
        }

    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete-agent/{room_name}")
async def delete_agent(room_name: str):
    """
    Delete a room when the agent is no longer needed.
    Call this when a client cancels their subscription.
    """
    try:
        lk = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_KEY,
            api_secret=LIVEKIT_SECRET,
        )
        await lk.room.delete_room(
            api.DeleteRoomRequest(room=room_name)
        )
        await lk.aclose()

        logger.info(f"Deleted room {room_name}")
        return {"status": "success", "message": f"Agent {room_name} deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "livekit_url": LIVEKIT_URL,
        "mcp_url": MCP_URL,
    }


@app.get("/")
def root():
    return {
        "message": "WeBuildFlows Voice Agent Server",
        "endpoints": {
            "POST /create-agent": "Create a new voice agent room",
            "DELETE /delete-agent/{room_name}": "Delete an agent room",
            "GET /health": "Health check",
        }
    }
