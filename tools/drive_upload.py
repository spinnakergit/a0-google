from helpers.tool import Tool, Response


class DriveUpload(Tool):
    """Upload a local file to Google Drive."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("drive", self.agent):
            return Response(
                message="Drive service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.drive_client import DriveClient, format_file

        file_path = self.args.get("file_path", "")
        name = self.args.get("name", "")
        folder_id = self.args.get("folder_id", "")
        description = self.args.get("description", "")

        if not file_path:
            return Response(
                message="Error: file_path is required. Provide the local path to the file to upload.",
                break_loop=False,
            )

        # Path safety — prevent uploading sensitive files or symlink traversal
        from pathlib import Path
        resolved = Path(file_path).resolve()
        blocked_paths = ["/a0/usr/plugins", "/a0/plugins", "/etc", "/root"]
        if any(str(resolved).startswith(d) for d in blocked_paths):
            return Response(
                message="Error: Cannot upload files from restricted directories. "
                        "Use files from /a0/usr/workdir/ instead.",
                break_loop=False,
            )
        if resolved.is_symlink():
            return Response(
                message="Error: Cannot upload symlinked files for security reasons.",
                break_loop=False,
            )

        client = DriveClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Drive unavailable. {DriveClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            self.set_progress(f"Uploading '{file_path}' to Drive...")

            result = client.upload_file(
                local_path=file_path,
                name=name,
                folder_id=folder_id,
                description=description,
            )

            file_info = format_file(result)
            return Response(
                message=f"File uploaded successfully.\n\n{file_info}",
                break_loop=True,
            )

        except FileNotFoundError:
            return Response(
                message=f"Error: File not found at '{file_path}'. Check the path and try again.",
                break_loop=False,
            )
        except Exception as e:
            return Response(
                message=f"Error uploading to Drive: {e}",
                break_loop=False,
            )
