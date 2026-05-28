from helpers.tool import Tool, Response


class DriveSearch(Tool):
    """Search files in Google Drive by name or content using full-text search."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("drive", self.agent):
            return Response(
                message="Drive service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.drive_client import DriveClient, format_file_list

        query = self.args.get("query", "")
        limit = int(self.args.get("limit", "20"))

        if not query:
            return Response(
                message="Error: query is required. Provide a search term to find files.",
                break_loop=False,
            )

        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        client = DriveClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Drive unavailable. {DriveClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            self.set_progress(f"Searching Drive for '{query}'...")

            files = client.search_files(query=query, max_results=limit)

            if not files:
                return Response(
                    message=f"No files found matching '{query}'.",
                    break_loop=False,
                )

            header = f"Found {len(files)} file(s) matching '{query}':"
            result = format_file_list(files)
            return Response(message=f"{header}\n\n{result}", break_loop=False)

        except Exception as e:
            return Response(
                message=f"Error searching Drive: {e}",
                break_loop=False,
            )
