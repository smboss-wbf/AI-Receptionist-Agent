"""
MCP Server — exposes calendar tools via Model Context Protocol (MCP)

What is MCP?
- MCP (Model Context Protocol) is an open standard by Anthropic
- It lets AI agents call external tools in a standardised way
- The agent connects to this server and discovers available tools automatically
- When the LLM decides to call a tool, it sends a request here
- This server executes the tool and returns the result to the agent

Architecture:
    agent.py (LiveKit) → MCP Client → [HTTP/SSE] → mcp_server.py → Google Calendar API

Run this first before agent.py:
    python mcp_server.py
"""

from mcp.server.fastmcp import FastMCP
from tools.calendar import check_availability, book_appointment
import uvicorn

# Create MCP server instance
mcp = FastMCP("dental-clinic-tools",)


@mcp.tool()
def check_availability_tool(date: str) -> str:
    """
    Check available appointment slots for a given date at Sharma Dental Clinic.

    Args:
        date: Date to check in YYYY-MM-DD format e.g. "2026-06-13"

    Returns:
        Description of available and busy slots for that date
    """
    return check_availability(date)


@mcp.tool()
def book_appointment_tool(
    caller_name: str,
    service: str,
    start_time: str,
    end_time: str
) -> str:
    """
    Book a dental appointment for the caller.
    IMPORTANT: Always call check_availability_tool first before booking.

    Args:
        caller_name: Full name of the patient e.g. "Rahul Sharma"
        service: Dental service e.g. "Regular checkup", "Tooth filling", "Root canal"
        start_time: Appointment start in ISO 8601 e.g. "2026-06-13T10:00:00+05:30"
        end_time: Appointment end in ISO 8601 e.g. "2026-06-13T10:30:00+05:30"

    Returns:
        Booking confirmation with details
    """
    return book_appointment(caller_name, service, start_time, end_time)


if __name__ == "__main__":
    print("Starting MCP server on http://localhost:9000")
    print("Tools available:")
    print("  - check_availability_tool")
    print("  - book_appointment_tool")
    print("\nAgent can connect at: http://localhost:9000/sse")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=9000)
