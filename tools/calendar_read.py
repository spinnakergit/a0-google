from helpers.tool import Tool, Response


class CalendarRead(Tool):
    """Read events from Google Calendar."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("calendar", self.agent):
            return Response(
                message="Calendar service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        action = self.args.get("action", "today")
        calendar_id = self.args.get("calendar_id", "")
        days = self.args.get("days", "7")
        start_date = self.args.get("start_date", "")
        end_date = self.args.get("end_date", "")
        event_id = self.args.get("event_id", "")
        limit = self.args.get("limit", "")

        from usr.plugins.google.helpers.calendar_client import (
            CalendarClient, format_events, format_event,
        )
        from usr.plugins.google.helpers.google_auth import get_google_config

        config = get_google_config(self.agent)
        if not calendar_id:
            calendar_id = config.get("defaults", {}).get("calendar_id", "primary")
        max_results = int(limit) if limit else config.get("defaults", {}).get("max_results", 10)
        timezone = config.get("defaults", {}).get("timezone", "America/New_York")

        self.set_progress("Connecting to Google Calendar...")
        client = CalendarClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Calendar unavailable. {CalendarClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            if action == "event" and event_id:
                event = client.get_event(event_id, calendar_id)
                return Response(message=format_event(event, timezone), break_loop=False)

            elif action == "today":
                from datetime import datetime, timedelta
                now = datetime.now()
                time_min = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
                time_max = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
                events = client.get_events(calendar_id, time_min, time_max, max_results)
                header = f"**Today's Events ({now.strftime('%A, %B %d, %Y')}):**\n\n"
                return Response(message=header + format_events(events, timezone), break_loop=False)

            elif action == "upcoming":
                from datetime import datetime, timedelta
                now = datetime.now()
                num_days = int(days)
                time_min = now.isoformat() + "Z"
                time_max = (now + timedelta(days=num_days)).isoformat() + "Z"
                events = client.get_events(calendar_id, time_min, time_max, max_results)
                header = f"**Upcoming Events (next {num_days} days):**\n\n"
                return Response(message=header + format_events(events, timezone), break_loop=False)

            elif action == "range":
                if not start_date or not end_date:
                    return Response(
                        message="Error: Both start_date and end_date are required for range queries.",
                        break_loop=False,
                    )
                from usr.plugins.google.helpers.date_utils import parse_datetime
                time_min = parse_datetime(start_date, timezone)
                time_max = parse_datetime(end_date, timezone)
                if not time_min or not time_max:
                    return Response(
                        message="Error: Could not parse date range. Use ISO format (YYYY-MM-DD) or natural language.",
                        break_loop=False,
                    )
                if "T" not in time_min:
                    time_min += "T00:00:00Z"
                else:
                    time_min += "Z"
                if "T" not in time_max:
                    time_max += "T23:59:59Z"
                else:
                    time_max += "Z"
                events = client.get_events(calendar_id, time_min, time_max, max_results)
                header = f"**Events from {start_date} to {end_date}:**\n\n"
                return Response(message=header + format_events(events, timezone), break_loop=False)

            elif action == "calendars":
                calendars = client.list_calendars()
                if not calendars:
                    return Response(message="No calendars found.", break_loop=False)
                lines = ["**Available Calendars:**\n"]
                for cal in calendars:
                    primary = " (primary)" if cal.get("primary") else ""
                    lines.append(f"- **{cal.get('summary', 'Untitled')}**{primary}")
                    lines.append(f"  ID: {cal.get('id', '')}")
                    if cal.get("description"):
                        lines.append(f"  Description: {cal['description']}")
                return Response(message="\n".join(lines), break_loop=False)

            else:
                return Response(
                    message=f"Error: Unknown action '{action}'. Use: today, upcoming, range, event, or calendars.",
                    break_loop=False,
                )
        except Exception as e:
            return Response(message=f"Error reading calendar: {e}", break_loop=False)
