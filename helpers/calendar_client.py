"""Google Calendar API client wrapper.

Handles all Calendar API operations. Auth is delegated to google_auth.
"""

import logging
from datetime import timedelta
from typing import Optional

from usr.plugins.google.helpers.google_auth import (
    get_google_config, build_service, GoogleAuthError,
)

logger = logging.getLogger("google.calendar_client")


class CalendarClient:
    """Google Calendar API wrapper with full CRUD operations."""

    last_error: str = ""

    def __init__(self, service):
        self._service = service

    @classmethod
    def from_config(cls, agent=None) -> Optional["CalendarClient"]:
        """Build a CalendarClient from plugin config. Returns None if unavailable."""
        config = get_google_config(agent)
        try:
            service = build_service("calendar", config)
            cls.last_error = ""
            return cls(service=service)
        except GoogleAuthError as e:
            cls.last_error = f"Auth: {e}"
            logger.warning("[google-plugin] CalendarClient auth failed: %s", e)
            return None
        except Exception as e:
            cls.last_error = f"{type(e).__name__}: {e}"
            logger.warning("[google-plugin] CalendarClient build failed: %s: %s", type(e).__name__, e)
            return None

    # --- Calendar listing ---

    def list_calendars(self) -> list:
        """List all calendars the user has access to."""
        result = self._service.calendarList().list().execute()
        return result.get("items", [])

    # --- Event read operations ---

    def get_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> list:
        """Fetch events from a calendar within a time range."""
        kwargs = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": single_events,
            "orderBy": order_by,
        }
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max

        result = self._service.events().list(**kwargs).execute()
        return result.get("items", [])

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict:
        """Get a specific event by ID."""
        return self._service.events().get(
            calendarId=calendar_id, eventId=event_id
        ).execute()

    # --- Event create ---

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
        attendees: Optional[list] = None,
        recurrence: Optional[list] = None,
        calendar_id: str = "primary",
        timezone: str = "America/New_York",
    ) -> dict:
        """Create a new calendar event."""
        event = {
            "summary": summary,
            "start": self._build_datetime(start, timezone),
            "end": self._build_datetime(end, timezone),
        }
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": a} for a in attendees]
        if recurrence:
            event["recurrence"] = recurrence

        return self._service.events().insert(
            calendarId=calendar_id, body=event,
            sendUpdates="all" if attendees else "none"
        ).execute()

    # --- Event update ---

    def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list] = None,
        timezone: str = "America/New_York",
    ) -> dict:
        """Update an existing event. Only provided fields are changed."""
        existing = self.get_event(event_id, calendar_id)

        if summary is not None:
            existing["summary"] = summary
        if start is not None:
            existing["start"] = self._build_datetime(start, timezone)
        if end is not None:
            existing["end"] = self._build_datetime(end, timezone)
        if description is not None:
            existing["description"] = description
        if location is not None:
            existing["location"] = location
        if attendees is not None:
            existing["attendees"] = [{"email": a} for a in attendees]

        return self._service.events().update(
            calendarId=calendar_id, eventId=event_id, body=existing,
            sendUpdates="all" if attendees else "none"
        ).execute()

    # --- Event delete ---

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> None:
        """Delete/cancel an event."""
        self._service.events().delete(
            calendarId=calendar_id, eventId=event_id,
            sendUpdates="all" if send_notifications else "none"
        ).execute()

    # --- Free/busy ---

    def get_free_busy(
        self,
        time_min: str,
        time_max: str,
        calendars: Optional[list] = None,
    ) -> dict:
        """Query free/busy information for calendars."""
        if calendars is None:
            calendars = ["primary"]

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": c} for c in calendars],
        }
        result = self._service.freebusy().query(body=body).execute()
        return result.get("calendars", {})

    def find_free_slots(
        self,
        time_min: str,
        time_max: str,
        duration_minutes: int = 60,
        calendars: Optional[list] = None,
    ) -> list:
        """Find available time slots of a given duration within a range."""
        from dateutil.parser import isoparse

        freebusy = self.get_free_busy(time_min, time_max, calendars)
        busy_periods = []
        for cal_id, cal_data in freebusy.items():
            for period in cal_data.get("busy", []):
                busy_periods.append((
                    isoparse(period["start"]),
                    isoparse(period["end"]),
                ))

        busy_periods.sort(key=lambda x: x[0])

        merged = []
        for start, end in busy_periods:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        duration = timedelta(minutes=duration_minutes)
        range_start = isoparse(time_min)
        range_end = isoparse(time_max)

        free_slots = []
        current = range_start

        for busy_start, busy_end in merged:
            if busy_start > current:
                gap = busy_start - current
                if gap >= duration:
                    free_slots.append({
                        "start": current.isoformat(),
                        "end": busy_start.isoformat(),
                        "duration_minutes": int(gap.total_seconds() / 60),
                    })
            current = max(current, busy_end)

        if range_end > current:
            gap = range_end - current
            if gap >= duration:
                free_slots.append({
                    "start": current.isoformat(),
                    "end": range_end.isoformat(),
                    "duration_minutes": int(gap.total_seconds() / 60),
                })

        return free_slots

    # --- Helpers ---

    def _build_datetime(self, dt_str: str, timezone: str) -> dict:
        """Build a Google Calendar datetime object from an ISO string."""
        if "T" in dt_str:
            return {"dateTime": dt_str, "timeZone": timezone}
        else:
            return {"date": dt_str}


def format_event(event: dict, timezone: str = "America/New_York") -> str:
    """Format a single event for display."""
    summary = event.get("summary", "(No title)")
    start = event.get("start", {})
    end = event.get("end", {})

    start_str = start.get("dateTime", start.get("date", ""))
    end_str = end.get("dateTime", end.get("date", ""))

    if "T" in start_str:
        start_str = start_str[:19].replace("T", " ")
    if "T" in end_str:
        end_str = end_str[:19].replace("T", " ")

    parts = [f"**{summary}**"]
    parts.append(f"  Time: {start_str} - {end_str}")

    if event.get("location"):
        parts.append(f"  Location: {event['location']}")
    if event.get("description"):
        desc = event["description"]
        if len(desc) > 200:
            desc = desc[:200] + "..."
        parts.append(f"  Description: {desc}")

    attendees = event.get("attendees", [])
    if attendees:
        names = [a.get("email", "") for a in attendees[:5]]
        att_str = ", ".join(names)
        if len(attendees) > 5:
            att_str += f" (+{len(attendees) - 5} more)"
        parts.append(f"  Attendees: {att_str}")

    status = event.get("status", "confirmed")
    if status != "confirmed":
        parts.append(f"  Status: {status}")

    event_id = event.get("id", "")
    if event_id:
        parts.append(f"  ID: {event_id}")

    if event.get("recurrence"):
        parts.append(f"  Recurrence: {', '.join(event['recurrence'])}")

    return "\n".join(parts)


def format_events(events: list, timezone: str = "America/New_York") -> str:
    """Format a list of events for display."""
    if not events:
        return "No events found."
    return "\n\n".join(format_event(e, timezone) for e in events)
