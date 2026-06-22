"""
Server — FastAPI server that creates voice agent rooms.

Accepts config from n8n HTTP Request node and creates a LiveKit room.
agent.py dev reads the room metadata and configures itself.

Run alongside agent.py:
    Terminal 1: python agent.py dev
    Terminal 2: uvicorn server:app --host 0.0.0.0 --port 8001 --reload
    Terminal 3: ngrok http 8001  (expose to n8n)
"""

import os
import json
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
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


# ─── Speaker map ─────────────────────────────────────────────────────────────

SPEAKER_MAP = {
    "Female":  "priya",
    "Male":    "rahul",
    "priya":   "priya",
    "rahul":   "rahul",
    "neha":    "neha",
    "ananya":  "ananya",
    "mithali": "mithali",
    "arjun":   "arjun",
    "siya":    "siya",
    "amol":    "amol",
}


# ─── Request model ────────────────────────────────────────────────────────────
# Accepts both n8n field names (system_prompt) and server field names (knowledge_file)

class AgentRequest(BaseModel):
    agent_name:     str                        # e.g. "Priya"
    agent_type:     str   = "Receptionist"
    voice_gender:   str   = "Female"           # Female / Male / exact speaker
    speaker:        Optional[str] = None       # override voice_gender if set

    # n8n sends "system_prompt", direct API sends "knowledge_file" — accept both
    system_prompt:  Optional[str] = None
    knowledge_file: Optional[str] = None

    # n8n specific fields — accepted but not used by agent.py directly
    tools:          Optional[List[str]] = []
    mcp_url:        Optional[str] = ""
    notify_email:   Optional[str] = ""
    runId:          Optional[str] = ""
    callback_url:   Optional[str] = ""
    user_id:        Optional[str] = ""


class TokenRequest(BaseModel):
    room_name:        str
    participant_name: str = "caller"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def resolve_prompt(request: AgentRequest) -> str:
    """Accept system_prompt (n8n) or knowledge_file (direct API), fallback to default."""
    prompt = request.system_prompt or request.knowledge_file or ""
    return prompt.strip() if prompt.strip() else DENTAL_CLINIC_PROMPT


def resolve_speaker(request: AgentRequest) -> str:
    """Accept explicit speaker name or map from voice_gender."""
    if request.speaker and request.speaker in SPEAKER_MAP:
        return SPEAKER_MAP[request.speaker]
    return SPEAKER_MAP.get(request.voice_gender, "priya")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.post("/create-agent")
async def create_agent(request: AgentRequest):
    """
    Called by n8n HTTP Request node after Build Prompt node.
    Creates a LiveKit room with agent config in metadata.
    agent.py dev picks it up automatically.
    """
    try:
        speaker       = resolve_speaker(request)
        system_prompt = resolve_prompt(request)
        room_name     = f"agent-{uuid.uuid4().hex[:8]}"

        # Everything agent.py needs is in this metadata JSON
        metadata = json.dumps({
            "system_prompt": system_prompt,
            "speaker":       speaker,
            "agent_type":    request.agent_type,
            "agent_name":    request.agent_name,
            "notify_email":  request.notify_email,
            "user_id":       request.user_id or request.runId,
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
                empty_timeout=86400,
            )
        )
        await lk.aclose()

        logger.info(f"✅ Room created: {room_name} | Agent: {request.agent_name} | Speaker: {speaker}")

        response = {
            "status":     "success",
            "agent_id":   room_name,
            "room_name":  room_name,
            "agent_name": request.agent_name,
            "speaker":    speaker,
            "livekit_url": LIVEKIT_URL,
            "message":    f"Agent '{request.agent_name}' is ready. Room: {room_name}",
        }

        return response

    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-token")
async def get_token(request: TokenRequest):
    """
    Generate a LiveKit access token for a caller to join the room.
    Call this after /create-agent to get the join token.
    """
    try:
        token = api.AccessToken(LIVEKIT_KEY, LIVEKIT_SECRET)
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=request.room_name,
            can_publish=True,
            can_subscribe=True,
        ))
        jwt = token.to_jwt()

        return {
            "status":      "success",
            "token":       jwt,
            "room_name":   request.room_name,
            "livekit_url": LIVEKIT_URL,
        }

    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete-agent/{room_name}")
async def delete_agent(room_name: str):
    """Delete a room when the agent session ends."""
    try:
        lk = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_KEY,
            api_secret=LIVEKIT_SECRET,
        )
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        await lk.aclose()
        return {"status": "success", "message": f"Room {room_name} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-agents")
async def list_agents():
    """List all active agent rooms — useful for your dashboard."""
    try:
        lk = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_KEY,
            api_secret=LIVEKIT_SECRET,
        )
        rooms = await lk.room.list_rooms(api.ListRoomsRequest())
        await lk.aclose()
        return {
            "status": "success",
            "count": len(rooms.rooms),
            "agents": [
                {
                    "room_name":        r.name,
                    "num_participants": r.num_participants,
                    "config": json.loads(r.metadata) if r.metadata else {},
                }
                for r in rooms.rooms
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "livekit_url": LIVEKIT_URL}


@app.get("/")
def root():
    return {
        "service": "WeBuildFlows Voice Agent Server",
        "endpoints": {
            "POST /create-agent":             "Create agent room (called by n8n)",
            "POST /get-token":                "Get caller token for a room",
            "DELETE /delete-agent/{room}":    "Delete agent room",
            "GET /list-agents":               "List all active rooms",
            "GET /health":                    "Health check",
        }
    }
