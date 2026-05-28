from helpers.tool import Tool, Response


class DriveShare(Tool):
    """Share a Google Drive file with a user or enable link sharing."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("drive", self.agent):
            return Response(
                message="Drive service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.drive_client import DriveClient

        file_id = self.args.get("file_id", "")
        email = self.args.get("email", "")
        role = self.args.get("role", "reader")
        link_sharing = self.args.get("link_sharing", "")

        if not file_id:
            return Response(
                message="Error: file_id is required. Provide the Google Drive file ID to share.",
                break_loop=False,
            )

        # Parse link_sharing as boolean
        link_sharing_bool = str(link_sharing).lower() in ("true", "1", "yes")

        if not email and not link_sharing_bool:
            return Response(
                message="Error: Either email or link_sharing=true is required. "
                        "Provide an email address to share with a specific user, "
                        "or set link_sharing=true to enable anyone-with-link access.",
                break_loop=False,
            )

        # Validate role
        valid_roles = ("reader", "writer", "commenter")
        if role not in valid_roles:
            return Response(
                message=f"Error: Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}.",
                break_loop=False,
            )

        client = DriveClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Drive unavailable. {DriveClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            # Get file name for the response
            self.set_progress("Updating sharing settings...")
            metadata = client.get_file_metadata(file_id)
            file_name = metadata.get("name", "unknown")

            result = client.share_file(
                file_id=file_id,
                email=email,
                role=role,
                link_sharing=link_sharing_bool,
            )

            sharing_link = result.get("webViewLink", "")
            lines = [f"Sharing updated for '{file_name}'."]

            if email:
                lines.append(f"  Shared with: {email} ({role})")
            if link_sharing_bool:
                lines.append(f"  Link sharing: enabled ({role})")
            if sharing_link:
                lines.append(f"  Link: {sharing_link}")

            return Response(message="\n".join(lines), break_loop=True)

        except ValueError as e:
            return Response(message=f"Error: {e}", break_loop=False)
        except Exception as e:
            return Response(
                message=f"Error sharing Drive file: {e}",
                break_loop=False,
            )
