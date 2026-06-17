"""
Google Calendar tools for the AI Receptionist.
Uses run_in_executor to avoid blocking the LiveKit async event loop.
"""

import os
import asyncio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def get_calendar_service():
    if not os.path.exists('token.json'):
        raise FileNotFoundError("token.json not found. Run setup_google_auth.py first.")

    creds = Credentials.from_authorized_user_file(
        'token.json',
        ['https://www.googleapis.com/auth/calendar']
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open('token.json', 'w') as f:
            f.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def _check_availability_sync(date: str) -> str:
    try:
        service = get_calendar_service()
        time_min = f"{date}T00:00:00+05:30"
        time_max = f"{date}T23:59:59+05:30"

        result = service.freebusy().query(body={
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": "Asia/Kolkata",
            "items": [{"id": "primary"}]
        }).execute()

        busy_slots = result["calendars"]["primary"]["busy"]

        if not busy_slots:
            return "Available."

        busy_times = [f"{s['start'][11:16]}-{s['end'][11:16]}" for s in busy_slots]
        return f"Busy: {', '.join(busy_times)}. Other slots free."

    except Exception as e:
        return f"Error: {str(e)}"


def _book_appointment_sync(caller_name: str, service: str, start_time: str, end_time: str) -> str:
    try:
        calendar_service = get_calendar_service()

        event = {
            "summary": f"{service} — {caller_name}",
            "description": f"Patient: {caller_name}\nService: {service}",
            "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
            "reminders": {"useDefault": True},
        }

        calendar_service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        date_str = start_time[5:10]
        time_str = start_time[11:16]
        return f"Confirmed. {caller_name}, {service}, {date_str} at {time_str}."

    except Exception as e:
        return f"Error: {str(e)}"


async def check_availability(date: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_availability_sync, date)


async def book_appointment(caller_name: str, service: str, start_time: str, end_time: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _book_appointment_sync, caller_name, service, start_time, end_time)