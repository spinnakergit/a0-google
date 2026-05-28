"""Google Sheets API client wrapper.

Handles spreadsheet creation, metadata retrieval, and cell-range
read/write/append. Spreadsheet listing is delegated to Drive (the Sheets
API does not expose a list endpoint).

Auth is delegated to google_auth.
"""

import logging
from typing import Optional

from usr.plugins.google.helpers.google_auth import (
    get_google_config, build_service, GoogleAuthError,
)

logger = logging.getLogger("google.sheets_client")

SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


class SheetsClient:
    """Google Sheets API wrapper."""

    last_error: str = ""

    def __init__(self, service):
        self._service = service

    @classmethod
    def from_config(cls, agent=None) -> Optional["SheetsClient"]:
        """Build a SheetsClient from plugin config. Returns None if unavailable."""
        config = get_google_config(agent)
        try:
            service = build_service("sheets", config)
            cls.last_error = ""
            return cls(service=service)
        except GoogleAuthError as e:
            cls.last_error = f"Auth: {e}"
            logger.warning("[google-plugin] SheetsClient auth failed: %s", e)
            return None
        except Exception as e:
            cls.last_error = f"{type(e).__name__}: {e}"
            logger.warning("[google-plugin] SheetsClient build failed: %s: %s", type(e).__name__, e)
            return None

    def create_spreadsheet(self, title: str, sheet_titles: Optional[list] = None) -> dict:
        """Create a new spreadsheet.

        sheet_titles: optional list of tab names. If omitted, one default tab is created.
        Returns the API response (includes spreadsheetId and spreadsheetUrl).
        """
        body: dict = {"properties": {"title": title}}
        if sheet_titles:
            body["sheets"] = [
                {"properties": {"title": t}} for t in sheet_titles if t
            ]
        return self._service.spreadsheets().create(
            body=body,
            fields="spreadsheetId,spreadsheetUrl,properties.title,sheets.properties",
        ).execute()

    def get_spreadsheet(self, spreadsheet_id: str) -> dict:
        """Get spreadsheet metadata (title, tabs, URL). Does not include cell values."""
        return self._service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="spreadsheetId,spreadsheetUrl,properties.title,sheets.properties",
        ).execute()

    def read_range(self, spreadsheet_id: str, range_a1: str) -> list:
        """Read a cell range. Returns a list of rows (each row a list of cell values)."""
        result = self._service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
        ).execute()
        return result.get("values", [])

    def write_range(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list,
        value_input_option: str = "USER_ENTERED",
    ) -> dict:
        """Write values to a cell range (overwrites existing cells).

        value_input_option: "USER_ENTERED" parses strings like dates/formulas;
        "RAW" stores them literally.
        """
        body = {"values": values}
        return self._service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption=value_input_option,
            body=body,
        ).execute()

    def append_range(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list,
        value_input_option: str = "USER_ENTERED",
    ) -> dict:
        """Append rows after the last row of data in the given range/table."""
        body = {"values": values}
        return self._service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption=value_input_option,
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()


def format_spreadsheet(spreadsheet: dict) -> str:
    """Format spreadsheet metadata for display."""
    sid = spreadsheet.get("spreadsheetId", "")
    url = spreadsheet.get("spreadsheetUrl", "")
    props = spreadsheet.get("properties", {}) or {}
    title = props.get("title", "Untitled")
    sheets = spreadsheet.get("sheets", []) or []

    parts = [f"**{title}**", f"  ID: {sid}"]
    if url:
        parts.append(f"  Link: {url}")
    if sheets:
        tab_names = [
            (s.get("properties", {}) or {}).get("title", "")
            for s in sheets
        ]
        tab_names = [t for t in tab_names if t]
        if tab_names:
            parts.append(f"  Tabs ({len(tab_names)}): {', '.join(tab_names)}")
    return "\n".join(parts)


def format_values(values: list, max_rows: int = 50, max_col_width: int = 40) -> str:
    """Render a values matrix as a plain-text table."""
    if not values:
        return "(empty range)"

    rows = values[:max_rows]
    truncated = len(values) > max_rows

    # Normalize rows to equal length so columns align.
    width = max(len(r) for r in rows)
    norm = [list(r) + [""] * (width - len(r)) for r in rows]

    def cell(v):
        s = "" if v is None else str(v)
        if len(s) > max_col_width:
            s = s[: max_col_width - 1] + "…"
        return s

    norm = [[cell(v) for v in r] for r in norm]
    col_widths = [
        max(len(r[c]) for r in norm) for c in range(width)
    ]

    lines = []
    for r in norm:
        lines.append(" | ".join(r[c].ljust(col_widths[c]) for c in range(width)))
    if truncated:
        lines.append(f"... ({len(values) - max_rows} more rows)")
    return "\n".join(lines)
