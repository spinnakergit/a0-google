from helpers.tool import Tool, Response


class CalendarCreate(Tool):
    """Create a new Google Calendar event."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("calendar", self.agent):
            return Response(
                message="Calendar service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        title = self.args.get("title", "")
        start = self.args.get("start", "")
        end = self.args.get("end", "")
        description = self.args.get("description", "")
        location = self.args.get("location", "")
        attendees = self.args.get("attendees", "")
        recurrence = self.args.get("recurrence", "")
        calendar_id = self.args.get("calendar_id", "")
        duration = self.args.get("duration", "")

        if not title:
            return Response(message="Error: Event title is required.", break_loop=False)
        if not start:
            return Response(message="Error: Event start time is required.", break_loop=False)

        from usr.plugins.google.helpers.calendar_client import (
            CalendarClient, format_event,
        )
        from usr.plugins.google.helpers.google_auth import get_google_config
        from usr.plugins.google.helpers.date_utils import (
            parse_datetime, parse_duration, compute_end_time,
        )

        config = get_google_config(self.agent)
        if not calendar_id:
            calendar_id = config.get("defaults", {}).get("calendar_id", "primary")
        timezone = config.get("defaults", {}).get("timezone", "America/New_York")
        default_duration = config.get("defaults", {}).get("default_duration_minutes", 60)
        max_attendees = config.get("security", {}).get("max_attendees", 50)

        # Parse start time
        parsed_start = parse_datetime(start, timezone)
        if not parsed_start:
            return Response(
                message=f"Error: Could not parse start time '{start}'. Use ISO format or natural language (e.g., 'tomorrow at 2pm').",
                break_loop=False,
            )

        # Parse end time or compute from duration
        if end:
            parsed_end = parse_datetime(end, timezone)
            if not parsed_end:
                return Response(
                    message=f"Error: Could not parse end time '{end}'.",
                    break_loop=False,
                )
        elif duration:
            dur_minutes = parse_duration(duration)
            if not dur_minutes:
                return Response(
                    message=f"Error: Could not parse duration '{duration}'. Use '1 hour', '30 minutes', '1h30m', etc.",
                    break_loop=False,
                )
            parsed_end = compute_end_time(parsed_start, dur_minutes)
        else:
            parsed_end = compute_end_time(parsed_start, default_duration)

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

        # Parse recurrence
        recurrence_list = None
        if recurrence:
            # Split on newlines for multiple rules, NOT semicolons (used within RRULE syntax)
            recurrence_list = [r.strip() for r in recurrence.split("\n") if r.strip()]
            # Ensure RRULE prefix
            recurrence_list = [
                r if r.startswith("RRULE:") else f"RRULE:{r}" for r in recurrence_list
            ]

        self.set_progress("Creating event...")
        client = CalendarClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message="Error: Google Calendar not authenticated. Please configure OAuth credentials in plugin settings.",
                break_loop=False,
            )

        try:
            event = client.create_event(
                summary=title,
                start=parsed_start,
                end=parsed_end,
                description=description,
                location=location,
                attendees=attendee_list,
                recurrence=recurrence_list,
                calendar_id=calendar_id,
                timezone=timezone,
            )
            result = f"Event created successfully!\n\n{format_event(event, timezone)}"
            if event.get("htmlLink"):
                result += f"\n\nLink: {event['htmlLink']}"
            return Response(message=result, break_loop=False)
        except Exception as e:
            return Response(message=f"Error creating event: {e}", break_loop=False)
