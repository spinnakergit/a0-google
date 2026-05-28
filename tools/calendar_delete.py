from helpers.tool import Tool, Response


class CalendarDelete(Tool):
    """Delete/cancel a Google Calendar event."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("calendar", self.agent):
            return Response(
                message="Calendar service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        event_id = self.args.get("event_id", "")
        calendar_id = self.args.get("calendar_id", "")
        send_notifications = self.args.get("send_notifications", "true")

        if not event_id:
            return Response(message="Error: event_id is required.", break_loop=False)

        from usr.plugins.google.helpers.calendar_client import (
            CalendarClient, format_event,
        )
        from usr.plugins.google.helpers.google_auth import get_google_config

        config = get_google_config(self.agent)
        if not calendar_id:
            calendar_id = config.get("defaults", {}).get("calendar_id", "primary")
        timezone = config.get("defaults", {}).get("timezone", "America/New_York")

        notify = send_notifications.lower() in ("true", "yes", "1")

        self.set_progress("Deleting event...")
        client = CalendarClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Calendar unavailable. {CalendarClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            # Fetch event details first for confirmation message
            event = client.get_event(event_id, calendar_id)
            summary = event.get("summary", "(No title)")

            client.delete_event(event_id, calendar_id, notify)
            msg = f"Event deleted: **{summary}** (ID: {event_id})"
            if notify:
                msg += "\nNotifications sent to attendees."
            return Response(message=msg, break_loop=False)
        except Exception as e:
            return Response(message=f"Error deleting event: {e}", break_loop=False)
