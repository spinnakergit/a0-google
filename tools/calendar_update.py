from helpers.tool import Tool, Response


class CalendarUpdate(Tool):
    """Update an existing Google Calendar event."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("calendar", self.agent):
            return Response(
                message="Calendar service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        event_id = self.args.get("event_id", "")
        title = self.args.get("title", "")
        start = self.args.get("start", "")
        end = self.args.get("end", "")
        description = self.args.get("description", "")
        location = self.args.get("location", "")
        attendees = self.args.get("attendees", "")
        calendar_id = self.args.get("calendar_id", "")

        if not event_id:
            return Response(message="Error: event_id is required.", break_loop=False)

        from usr.plugins.google.helpers.calendar_client import (
            CalendarClient, format_event,
        )
        from usr.plugins.google.helpers.google_auth import get_google_config
        from usr.plugins.google.helpers.date_utils import parse_datetime

        config = get_google_config(self.agent)
        if not calendar_id:
            calendar_id = config.get("defaults", {}).get("calendar_id", "primary")
        timezone = config.get("defaults", {}).get("timezone", "America/New_York")
        max_attendees = config.get("security", {}).get("max_attendees", 50)

        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        if start:
            parsed_start = parse_datetime(start, timezone)
            if not parsed_start:
                return Response(
                    message=f"Error: Could not parse start time '{start}'.",
                    break_loop=False,
                )
        if end:
            parsed_end = parse_datetime(end, timezone)
            if not parsed_end:
                return Response(
                    message=f"Error: Could not parse end time '{end}'.",
                    break_loop=False,
                )

        # Parse attendees (handle both string and list)
        attendee_list = None
        if attendees:
            if isinstance(attendees, str):
                attendee_list = [a.strip() for a in attendees.split(",") if a.strip()]
            else:
                attendee_list = [a.strip() for a in attendees if a.strip()]
            if len(attendee_list) > max_attendees:
                return Response(
                    message=f"Error: Too many attendees ({len(attendee_list)}). Maximum is {max_attendees}.",
                    break_loop=False,
                )

        self.set_progress("Updating event...")
        client = CalendarClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Calendar unavailable. {CalendarClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        # If start changed but end was not provided, preserve original duration
        if parsed_start and not parsed_end:
            try:
                from dateutil.parser import isoparse
                from usr.plugins.google.helpers.date_utils import compute_end_time
                existing = client.get_event(event_id, calendar_id)
                orig_start = existing.get("start", {}).get("dateTime", "")
                orig_end = existing.get("end", {}).get("dateTime", "")
                if orig_start and orig_end:
                    orig_dur = (isoparse(orig_end) - isoparse(orig_start)).total_seconds() / 60
                    parsed_end = compute_end_time(parsed_start, int(orig_dur))
            except Exception:
                pass  # Fall through — update start only if duration can't be preserved

        try:
            event = client.update_event(
                event_id=event_id,
                calendar_id=calendar_id,
                summary=title or None,
                start=parsed_start,
                end=parsed_end,
                description=description or None,
                location=location or None,
                attendees=attendee_list,
                timezone=timezone,
            )
            result = f"Event updated successfully!\n\n{format_event(event, timezone)}"
            return Response(message=result, break_loop=False)
        except Exception as e:
            return Response(message=f"Error updating event: {e}", break_loop=False)
