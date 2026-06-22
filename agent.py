"""
Voice Agent — AI Receptionist (single calendar, token.json / OAuth)

Uses your own Google Calendar via token.json (see setup_google_auth.py).
No calendar_id needed — tools/calendar.py always targets calendarId='primary'.
"""

import os
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import silero, openai
from livekit.plugins import sarvam

from prompts import DENTAL_CLINIC_PROMPT
from tools.calendar import _check_availability_sync, _book_appointment_sync

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger("voice-agent")

# Dedicated thread pool for calendar I/O — avoids event-loop blocking issues
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="calendar")


class DentalReceptionist(Agent):

    def __init__(self, instructions: str):
        super().__init__(instructions=instructions)

    @function_tool()
    async def check_availability_tool(
        self,
        context: RunContext,
        date: str,
    ) -> str:
        """
        Check available appointment slots for a given date.

        Args:
            date: Date in YYYY-MM-DD format e.g. 2026-06-16
        """
        logger.info(f"🔧 check_availability_tool ENTERED: date={date}")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _executor, _check_availability_sync, date
        )

        logger.info(f"✅ check_availability_tool RESULT: {result}")
        return result

    @function_tool()
    async def book_appointment_tool(
        self,
        context: RunContext,
        caller_name: str,
        service: str,
        start_time: str,
        end_time: str,
    ) -> str:
        """
        Book an appointment on the calendar.
        Always call check_availability_tool first before booking.

        Args:
            caller_name: Full name of the caller e.g. Shivansh Malhotra
            service: Service requested e.g. Regular checkup
            start_time: ISO 8601 start time e.g. 2026-06-16T16:00:00+05:30
            end_time: ISO 8601 end time e.g. 2026-06-16T16:30:00+05:30
        """
        logger.info(f"🔧 book_appointment_tool ENTERED: {caller_name} | {service} | {start_time}")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _executor, _book_appointment_sync, caller_name, service, start_time, end_time
        )

        logger.info(f"✅ book_appointment_tool RESULT: {result}")
        return result


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    try:
        meta = json.loads(ctx.room.metadata or '{}')
    except Exception:
        meta = {}

    if not meta.get('system_prompt'):
        try:
            meta = json.loads(ctx.job.metadata or '{}')
        except Exception:
            meta = {}

    system_prompt = meta.get('system_prompt') or DENTAL_CLINIC_PROMPT
    speaker       = meta.get('speaker', 'priya')

    logger.info(f"Speaker: {speaker}")
    logger.info(f"Prompt preview: {system_prompt[:80]}...")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=sarvam.STT(
            model="saaras:v3",
            language="en-IN",
            mode="codemix",
            flush_signal=True,
        ),
        llm=openai.LLM(model="gpt-4o"),
        tts=sarvam.TTS(
            model="bulbul:v3",
            target_language_code="en-IN",
            speaker=speaker,
            pace=1.1,
        ),
    )

    await session.start(
        room=ctx.room,
        agent=DentalReceptionist(instructions=system_prompt),
    )

    await session.generate_reply(
        instructions=(
            "Greet the caller warmly. "
            "Tell them they have reached the clinic. "
            "Ask how you can help."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="dental-receptionist",  # must match the agent_name in your LiveKit SIP dispatch rule
    ))
