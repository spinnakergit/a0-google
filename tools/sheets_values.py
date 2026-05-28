import json

from helpers.tool import Tool, Response


def _parse_values(raw):
    """Accept a 2D list directly, or a JSON-encoded 2D list as a string.

    Always returns a list of rows where each row is a list of cells.
    Raises ValueError with a friendly message on bad input.
    """
    if raw is None or raw == "":
        raise ValueError("values is required (a 2D array of rows).")

    if isinstance(raw, list):
        parsed = raw
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception as e:
            raise ValueError(f"values must be valid JSON (2D array): {e}")
    else:
        raise ValueError(f"values must be a list or JSON string, got {type(raw).__name__}.")

    if not isinstance(parsed, list) or not parsed:
        raise ValueError("values must be a non-empty list of rows.")

    # Normalize a 1D list into a single row (common agent mistake).
    if not isinstance(parsed[0], list):
        parsed = [parsed]

    return parsed


class SheetsValues(Tool):
    """Read, write, or append cell values in a Google spreadsheet range."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("sheets", self.agent):
            return Response(
                message="Sheets service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.sheets_client import (
            SheetsClient, format_values,
        )

        action = self.args.get("action", "")
        spreadsheet_id = self.args.get("spreadsheet_id", "")
        range_a1 = self.args.get("range", "")

        if not action:
            return Response(
                message="Error: action is required. Use: read, write, append.",
                break_loop=False,
            )
        if not spreadsheet_id:
            return Response(
                message="Error: spreadsheet_id is required.",
                break_loop=False,
            )
        if not range_a1:
            return Response(
                message="Error: range is required (A1 notation, e.g. 'Sheet1!A1:C10').",
                break_loop=False,
            )

        client = SheetsClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Sheets unavailable. {SheetsClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            if action == "read":
                return await self._read(client, format_values, spreadsheet_id, range_a1)
            elif action in ("write", "append"):
                return await self._write_or_append(client, action, spreadsheet_id, range_a1)
            else:
                return Response(
                    message=f"Unknown action '{action}'. Use: read, write, append.",
                    break_loop=False,
                )
        except ValueError as e:
            return Response(message=f"Error: {e}", break_loop=False)
        except Exception as e:
            return Response(
                message=f"Error on sheets {action}: {type(e).__name__}: {e}",
                break_loop=False,
            )

    async def _read(self, client, format_values, spreadsheet_id, range_a1) -> Response:
        self.set_progress(f"Reading {range_a1}...")
        rows = client.read_range(spreadsheet_id=spreadsheet_id, range_a1=range_a1)

        header = f"Range '{range_a1}' ({len(rows)} row{'s' if len(rows) != 1 else ''}):"
        if not rows:
            return Response(message=f"{header}\n(empty)", break_loop=False)

        return Response(
            message=f"{header}\n\n{format_values(rows)}",
            break_loop=False,
        )

    async def _write_or_append(self, client, action, spreadsheet_id, range_a1) -> Response:
        values = _parse_values(self.args.get("values"))
        value_input = self.args.get("value_input", "USER_ENTERED")
        if value_input not in ("USER_ENTERED", "RAW"):
            return Response(
                message=f"Error: value_input must be 'USER_ENTERED' or 'RAW' (got '{value_input}').",
                break_loop=False,
            )

        if action == "write":
            self.set_progress(f"Writing to {range_a1}...")
            result = client.write_range(
                spreadsheet_id=spreadsheet_id,
                range_a1=range_a1,
                values=values,
                value_input_option=value_input,
            )
            updated = result.get("updatedRange", range_a1)
            cells = result.get("updatedCells", 0)
            return Response(
                message=f"Wrote {cells} cell(s) to {updated}.",
                break_loop=True,
            )

        # append
        self.set_progress(f"Appending to {range_a1}...")
        result = client.append_range(
            spreadsheet_id=spreadsheet_id,
            range_a1=range_a1,
            values=values,
            value_input_option=value_input,
        )
        updates = result.get("updates", {}) or {}
        updated_range = updates.get("updatedRange", "")
        cells = updates.get("updatedCells", 0)
        suffix = f" ({updated_range})" if updated_range else ""
        return Response(
            message=f"Appended {cells} cell(s){suffix}.",
            break_loop=True,
        )
