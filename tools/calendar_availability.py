from helpers.tool import Tool, Response


class CalendarAvailability(Tool):
    """Check free/busy slots on Google Calendar."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("calendar", self.agent):
            return Response(
                message="Calendar service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        action = self.args.get("action", "free_slots")
        date = self.args.get("date", "")
        start_date = self.args.get("start_date", "")
        end_date = self.args.get("end_date", "")
        duration_minutes = self.args.get("duration_minutes", "")
        calendars = self.args.get("calendars", "")

        from usr.plugins.google.helpers.calendar_client import CalendarClient
        from usr.plugins.google.helpers.google_auth import get_google_config
        from usr.plugins.google.helpers.date_utils import parse_datetime

        config = get_google_config(self.agent)
        timezone = config.get("defaults", {}).get("timezone", "America/New_York")
        default_duration = config.get("defaults", {}).get("default_duration_minutes", 60)

        # Parse duration
        dur = int(duration_minutes) if duration_minutes else default_duration

        # Parse calendar list
        cal_list = None
        if calendars:
            cal_list = [c.strip() for c in calendars.split(",") if c.strip()]

        # Determine time range
        if date:
            parsed = parse_datetime(date, timezone)
            if not parsed:
                return Response(
                    message=f"Error: Could not parse date '{date}'.",
                    break_loop=False,
                )
            if "T" not in parsed:
                time_min = parsed + "T00:00:00Z"
                time_max = parsed + "T23:59:59Z"
            else:
                time_min = parsed + "Z"
                from usr.plugins.google.helpers.date_utils import compute_end_time
                time_max = compute_end_time(parsed, 24 * 60) + "Z"
        elif start_date and end_date:
            parsed_start = parse_datetime(start_date, timezone)
            parsed_end = parse_datetime(end_date, timezone)
            if not parsed_start or not parsed_end:
                return Response(
                    message="Error: Could not parse date range.",
                    break_loop=False,
                )
            time_min = (parsed_start + "T00:00:00Z") if "T" not in parsed_start else (parsed_start + "Z")
            time_max = (parsed_end + "T23:59:59Z") if "T" not in parsed_end else (parsed_end + "Z")
        else:
            # Default: today
            from datetime import datetime
            now = datetime.now()
            time_min = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            time_max = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        self.set_progress("Checking availability...")
        client = CalendarClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Calendar unavailable. {CalendarClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            if action == "busy":
                freebusy = client.get_free_busy(time_min, time_max, cal_list)
                lines = ["**Busy Periods:**\n"]
                for cal_id, cal_data in freebusy.items():
                    busy = cal_data.get("busy", [])
                    if busy:
                        lines.append(f"Calendar: {cal_id}")
                        for period in busy:
                            s = period["start"][:19].replace("T", " ")
                            e = period["end"][:19].replace("T", " ")
                            lines.append(f"  - {s} to {e}")
                    else:
                        lines.append(f"Calendar: {cal_id} -- No busy periods")
                return Response(message="\n".join(lines), break_loop=False)

            else:  # free_slots (default)
                free_slots = client.find_free_slots(time_min, time_max, dur, cal_list)
                if not free_slots:
                    return Response(
                        message=f"No free slots of {dur} minutes found in the specified range.",
                        break_loop=False,
                    )
                lines = [f"**Available Slots (minimum {dur} minutes):**\n"]
                for slot in free_slots:
                    s = slot["start"][:19].replace("T", " ")
                    e = slot["end"][:19].replace("T", " ")
                    lines.append(f"- {s} to {e} ({slot['duration_minutes']} min available)")
                return Response(message="\n".join(lines), break_loop=False)

        except Exception as e:
            return Response(message=f"Error checking availability: {e}", break_loop=False)
