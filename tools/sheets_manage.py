from helpers.tool import Tool, Response


class SheetsManage(Tool):
    """Manage Google Spreadsheets: create, get metadata, or list spreadsheets."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("sheets", self.agent):
            return Response(
                message="Sheets service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.sheets_client import (
            SheetsClient, format_spreadsheet, SPREADSHEET_MIME,
        )

        action = self.args.get("action", "")
        if not action:
            return Response(
                message="Error: action is required. Use: create, get, list.",
                break_loop=False,
            )

        client = SheetsClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Sheets unavailable. {SheetsClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            if action == "create":
                return await self._create(client, format_spreadsheet)
            elif action == "get":
                return await self._get(client, format_spreadsheet)
            elif action == "list":
                return await self._list(format_spreadsheet, SPREADSHEET_MIME)
            else:
                return Response(
                    message=f"Unknown action '{action}'. Use: create, get, list.",
                    break_loop=False,
                )
        except Exception as e:
            return Response(
                message=f"Error managing spreadsheet: {type(e).__name__}: {e}",
                break_loop=False,
            )

    async def _create(self, client, format_spreadsheet) -> Response:
        title = self.args.get("title", "")
        sheet_titles_raw = self.args.get("sheet_titles", "")

        if not title:
            return Response(
                message="Error: title is required to create a spreadsheet.",
                break_loop=False,
            )

        # Accept either a list (JSON array) or a comma-separated string.
        if isinstance(sheet_titles_raw, list):
            sheet_titles = [str(s).strip() for s in sheet_titles_raw if str(s).strip()]
        elif isinstance(sheet_titles_raw, str) and sheet_titles_raw.strip():
            sheet_titles = [s.strip() for s in sheet_titles_raw.split(",") if s.strip()]
        else:
            sheet_titles = None

        self.set_progress(f"Creating spreadsheet '{title}'...")
        result = client.create_spreadsheet(title=title, sheet_titles=sheet_titles)
        return Response(
            message=f"Spreadsheet created.\n\n{format_spreadsheet(result)}",
            break_loop=True,
        )

    async def _get(self, client, format_spreadsheet) -> Response:
        spreadsheet_id = self.args.get("spreadsheet_id", "")
        if not spreadsheet_id:
            return Response(
                message="Error: spreadsheet_id is required.",
                break_loop=False,
            )

        self.set_progress("Fetching spreadsheet metadata...")
        result = client.get_spreadsheet(spreadsheet_id=spreadsheet_id)
        return Response(
            message=format_spreadsheet(result),
            break_loop=False,
        )

    async def _list(self, format_spreadsheet, spreadsheet_mime) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("drive", self.agent):
            return Response(
                message="Error: listing spreadsheets requires the Drive service to be enabled "
                        "(the Sheets API itself does not list files). Enable Drive in plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.drive_client import DriveClient

        limit = int(self.args.get("limit", "25"))
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        drive = DriveClient.from_config(agent=self.agent)
        if not drive:
            return Response(
                message=f"Error: Google Drive unavailable. {DriveClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        self.set_progress("Listing spreadsheets via Drive...")
        files = drive.list_files(max_results=limit, mime_type=spreadsheet_mime)

        if not files:
            return Response(message="No spreadsheets found.", break_loop=False)

        lines = [f"Spreadsheets ({len(files)}):"]
        for f in files:
            name = f.get("name", "Untitled")
            sid = f.get("id", "")
            modified = (f.get("modifiedTime", "") or "")[:19].replace("T", " ")
            link = f.get("webViewLink", "")
            entry = [f"\n**{name}**", f"  ID: {sid}"]
            if modified:
                entry.append(f"  Modified: {modified}")
            if link:
                entry.append(f"  Link: {link}")
            lines.append("\n".join(entry))

        return Response(message="\n".join(lines), break_loop=False)
