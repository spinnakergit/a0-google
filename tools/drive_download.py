from helpers.tool import Tool, Response


class DriveDownload(Tool):
    """Download a file from Google Drive to a local path."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("drive", self.agent):
            return Response(
                message="Drive service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.drive_client import DriveClient

        file_id = self.args.get("file_id", "")
        local_path = self.args.get("local_path", "")

        if not file_id:
            return Response(
                message="Error: file_id is required. Provide the Google Drive file ID.",
                break_loop=False,
            )
        if not local_path:
            return Response(
                message="Error: local_path is required. Provide the destination path for the downloaded file.",
                break_loop=False,
            )

        # Path traversal protection — restrict downloads to safe directories
        from pathlib import Path
        safe_dirs = ["/a0/usr/workdir", "/a0/usr/files", "/tmp"]
        resolved = str(Path(local_path).resolve())
        if not any(resolved.startswith(d) for d in safe_dirs):
            return Response(
                message="Error: Downloads are restricted to the working directory. "
                        "Use a path under /a0/usr/workdir/ instead.",
                break_loop=False,
            )

        client = DriveClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Drive unavailable. {DriveClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            # Get file metadata first to show the user what's being downloaded
            self.set_progress("Fetching file metadata...")
            metadata = client.get_file_metadata(file_id)
            file_name = metadata.get("name", "unknown")
            mime_type = metadata.get("mimeType", "")

            # Google Docs types will be exported as PDF
            google_doc_types = {
                "application/vnd.google-apps.document": "PDF",
                "application/vnd.google-apps.spreadsheet": "PDF",
                "application/vnd.google-apps.presentation": "PDF",
            }
            export_note = ""
            if mime_type in google_doc_types:
                export_format = google_doc_types[mime_type]
                export_note = f" (exported as {export_format})"

            self.set_progress(f"Downloading '{file_name}'{export_note}...")

            saved_path = client.download_file(file_id=file_id, local_path=local_path)

            size_info = ""
            try:
                import os
                size = os.path.getsize(saved_path)
                if size > 1_000_000:
                    size_info = f" ({size / 1_000_000:.1f} MB)"
                elif size > 1_000:
                    size_info = f" ({size / 1_000:.1f} KB)"
                else:
                    size_info = f" ({size} B)"
            except OSError:
                pass

            return Response(
                message=f"File downloaded successfully.\n"
                        f"  Name: {file_name}{export_note}\n"
                        f"  Saved to: {saved_path}{size_info}",
                break_loop=True,
            )

        except Exception as e:
            return Response(
                message=f"Error downloading from Drive: {e}",
                break_loop=False,
            )
