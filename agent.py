"""
Voice Agent — AI Receptionist
Built with LiveKit Agents (agentic AI framework) + MCP + Sarvam AI

Architecture:
    Caller speaks
        → LiveKit captures audio
        → Sarvam STT (saaras:v3) converts voice to text
        → GPT-4o-mini (LLM) reads text, decides what to do
        → If tool needed: calls MCP server (calendar tools)
        → LLM generates reply text
        → Sarvam TTS (bulbul:v3) converts text to voice
        → Caller hears the response

Key frameworks used:
    - LiveKit Agents: agentic voice pipeline framework
    - MCP (Model Context Protocol): standardised tool calling protocol
    - FastMCP: Python MCP server implementation
    - Sarvam AI: Indian language STT + TTS
    - Silero VAD: voice activity detection

Run order:
    1. python mcp_server.py      (start MCP tool server)
    2. python agent.py dev       (start agent worker)
    3. python agent.py console   (test via text/mic)
"""

import os
import json
import logging
from dotenv import load_dotenv

from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.llm.mcp import MCPServerHTTP, MCPToolset
from livekit.plugins import silero, openai
from livekit.plugins import sarvam

from prompts import DENTAL_CLINIC_PROMPT, DEFAULT_PROMPT

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger("voice-agent")


async def entrypoint(ctx: JobContext):
    """
    Main agent entrypoint — called by LiveKit when a caller joins a room.

    Each room has metadata containing:
    - system_prompt: instructions for this specific agent/client
    - speaker: which Sarvam voice to use (priya, rahul, neha etc.)
    - mcp_url: which MCP server to connect to for tools

    This allows one codebase to serve multiple clients —
    each with their own prompt, voice, and tools.
    """

    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # ─── Step 1: Load configuration from room metadata ───────────────────────
    try:
        meta = json.loads(ctx.room.metadata or '{}')
    except Exception:
        meta = {}

    # Fallback to job metadata (LiveKit Cloud console testing)
    if not meta.get('system_prompt'):
        try:
            meta = json.loads(ctx.job.metadata or '{}')
        except Exception:
            meta = {}

    system_prompt = meta.get('system_prompt') or DENTAL_CLINIC_PROMPT
    speaker       = meta.get('speaker', 'priya')
    mcp_url       = meta.get('mcp_url') or os.getenv('MCP_URL', 'http://localhost:9000/sse')

    logger.info(f"Speaker: {speaker} | MCP: {mcp_url}")
    logger.info(f"Prompt preview: {system_prompt[:80]}...")

    # ─── Step 2: Connect to MCP tool server ──────────────────────────────────
    # MCPToolset connects to mcp_server.py
    # LLM discovers tools automatically and calls them during conversation
    tools = []
    try:
        mcp_toolset = MCPToolset(
            id="dental-tools",
            mcp_server=MCPServerHTTP(url=mcp_url),
        )
        tools.append(mcp_toolset)
        logger.info(f"MCP toolset connected: {mcp_url}")
    except Exception as e:
        logger.error(f"MCP connection failed: {e} — agent will run without tools")

    # ─── Step 3: Build the voice session ─────────────────────────────────────
    session = AgentSession(

        # VAD — detects when caller starts/stops speaking
        vad=silero.VAD.load(),

        # STT — Sarvam saaras:v3 — best for Indian languages + Hinglish
        stt=sarvam.STT(
            model="saaras:v3",
            language="en-IN",
            mode="codemix",
            flush_signal=True,
        ),

        # LLM — brain of the agent
        # Uses OpenAI function calling to invoke MCP tools
        llm=openai.LLM(model="gpt-4o-mini"),

        # TTS — Sarvam bulbul:v3 — natural Indian voice
        tts=sarvam.TTS(
            model="bulbul:v3",
            target_language_code="en-IN",
            speaker=speaker,
            pace=1.1,
        ),

    )

    # ─── Step 4: Start the agent session ─────────────────────────────────────
    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions=system_prompt,
            tools=tools,
        ),
    )

    # ─── Step 5: Greet the caller ─────────────────────────────────────────────
    await session.generate_reply(
        instructions=(
            "Greet the caller warmly. "
            "Tell them they have reached Sharma Dental Clinic. "
            "Ask how you can help. "
            "Speak naturally like a human receptionist. "
            "Never read out code, variable names, IDs, or technical terms. "
            "When tools return results, interpret them conversationally."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))