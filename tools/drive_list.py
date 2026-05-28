from helpers.tool import Tool, Response


class DriveList(Tool):
    """List files in Google Drive, optionally filtered by folder, MIME type, or ordering."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("drive", self.agent):
            return Response(
                message="Drive service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.drive_client import DriveClient, format_file_list

        folder_id = self.args.get("folder_id", "")
        mime_type = self.args.get("mime_type", "")
        limit = int(self.args.get("limit", "20"))
        order_by = self.args.get("order_by", "modifiedTime desc")

        # Cap limit to a sane maximum
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
            self.set_progress("Listing Drive files...")

            files = client.list_files(
                folder_id=folder_id,
                max_results=limit,
                mime_type=mime_type,
                order_by=order_by,
            )

            header_parts = [f"Google Drive files ({len(files)})"]
            if folder_id:
                header_parts.append(f"in folder {folder_id}")
            if mime_type:
                header_parts.append(f"type: {mime_type}")
            header = " ".join(header_parts) + ":"

            result = format_file_list(files)
            if files:
                result = f"{header}\n\n{result}"

            return Response(message=result, break_loop=False)

        except Exception as e:
            return Response(
                message=f"Error listing Drive files: {e}",
                break_loop=False,
            )
