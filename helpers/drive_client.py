"""Google Drive API client wrapper.

Handles file listing, searching, uploading, downloading, and sharing.
Auth is delegated to google_auth.
"""

import io
import os
import logging
from pathlib import Path
from typing import Optional

from usr.plugins.google.helpers.google_auth import (
    get_google_config, build_service, GoogleAuthError,
)

logger = logging.getLogger("google.drive_client")


class DriveClient:
    """Google Drive API wrapper."""

    # Diagnostic message from the most recent from_config() failure. Read by tools
    # to surface the real reason (instead of a generic "not authenticated").
    last_error: str = ""

    def __init__(self, service):
        self._service = service

    @classmethod
    def from_config(cls, agent=None) -> Optional["DriveClient"]:
        """Build a DriveClient from plugin config. Returns None if unavailable."""
        config = get_google_config(agent)
        try:
            service = build_service("drive", config)
            cls.last_error = ""
            return cls(service=service)
        except GoogleAuthError as e:
            cls.last_error = f"Auth: {e}"
            logger.warning("[google-plugin] DriveClient auth failed: %s", e)
            return None
        except Exception as e:
            cls.last_error = f"{type(e).__name__}: {e}"
            logger.warning("[google-plugin] DriveClient build failed: %s: %s", type(e).__name__, e)
            return None

    def list_files(
        self,
        folder_id: str = "",
        max_results: int = 20,
        mime_type: str = "",
        order_by: str = "modifiedTime desc",
    ) -> list:
        """List files, optionally filtered by folder or MIME type."""
        query_parts = ["trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        if mime_type:
            query_parts.append(f"mimeType = '{mime_type}'")

        result = self._service.files().list(
            q=" and ".join(query_parts),
            pageSize=max_results,
            orderBy=order_by,
            fields="files(id, name, mimeType, size, modifiedTime, owners, webViewLink, parents)",
        ).execute()
        return result.get("files", [])

    def search_files(self, query: str, max_results: int = 20) -> list:
        """Search files by name or full-text content."""
        q = f"fullText contains '{query}' and trashed = false"
        result = self._service.files().list(
            q=q,
            pageSize=max_results,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
        ).execute()
        return result.get("files", [])

    def get_file_metadata(self, file_id: str) -> dict:
        """Get metadata for a specific file."""
        return self._service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime, owners, webViewLink, parents, description",
        ).execute()

    def upload_file(
        self,
        local_path: str,
        name: str = "",
        folder_id: str = "",
        description: str = "",
    ) -> dict:
        """Upload a file to Google Drive."""
        from googleapiclient.http import MediaFileUpload

        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        file_name = name or path.name
        metadata = {"name": file_name}
        if folder_id:
            metadata["parents"] = [folder_id]
        if description:
            metadata["description"] = description

        media = MediaFileUpload(str(path), resumable=True)
        return self._service.files().create(
            body=metadata, media_body=media,
            fields="id, name, mimeType, size, webViewLink",
        ).execute()

    def download_file(self, file_id: str, local_path: str) -> str:
        """Download a file from Google Drive to a local path."""
        from googleapiclient.http import MediaIoBaseDownload

        metadata = self.get_file_metadata(file_id)
        mime_type = metadata.get("mimeType", "")

        # For Google Docs/Sheets/Slides, export as PDF
        export_mimes = {
            "application/vnd.google-apps.document": "application/pdf",
            "application/vnd.google-apps.spreadsheet": "application/pdf",
            "application/vnd.google-apps.presentation": "application/pdf",
        }

        dest_path = Path(local_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if mime_type in export_mimes:
            request = self._service.files().export_media(
                fileId=file_id, mimeType=export_mimes[mime_type]
            )
            if not dest_path.suffix:
                dest_path = dest_path.with_suffix(".pdf")
        else:
            request = self._service.files().get_media(fileId=file_id)

        with open(str(dest_path), "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return str(dest_path)

    def share_file(
        self,
        file_id: str,
        email: str = "",
        role: str = "reader",
        link_sharing: bool = False,
    ) -> dict:
        """Share a file with a user or enable link sharing."""
        if link_sharing:
            permission = {"type": "anyone", "role": role}
        elif email:
            permission = {"type": "user", "role": role, "emailAddress": email}
        else:
            raise ValueError("Either email or link_sharing must be specified.")

        result = self._service.permissions().create(
            fileId=file_id, body=permission,
            sendNotificationEmail=bool(email),
            fields="id, type, role",
        ).execute()

        # Get the sharing link
        file_meta = self._service.files().get(
            fileId=file_id, fields="webViewLink"
        ).execute()
        result["webViewLink"] = file_meta.get("webViewLink", "")
        return result

    def delete_file(self, file_id: str) -> None:
        """Move a file to trash."""
        self._service.files().update(
            fileId=file_id, body={"trashed": True}
        ).execute()


def format_file(f: dict) -> str:
    """Format a single file for display."""
    name = f.get("name", "Untitled")
    mime = f.get("mimeType", "unknown")
    size = f.get("size", "")
    modified = f.get("modifiedTime", "")[:19].replace("T", " ") if f.get("modifiedTime") else ""
    link = f.get("webViewLink", "")
    file_id = f.get("id", "")

    size_str = ""
    if size:
        size_int = int(size)
        if size_int > 1_000_000:
            size_str = f" ({size_int / 1_000_000:.1f} MB)"
        elif size_int > 1_000:
            size_str = f" ({size_int / 1_000:.1f} KB)"
        else:
            size_str = f" ({size_int} B)"

    parts = [f"**{name}**{size_str}"]
    parts.append(f"  Type: {mime}")
    if modified:
        parts.append(f"  Modified: {modified}")
    if link:
        parts.append(f"  Link: {link}")
    parts.append(f"  ID: {file_id}")
    return "\n".join(parts)


def format_file_list(files: list) -> str:
    """Format a list of files for display."""
    if not files:
        return "No files found."
    return "\n\n".join(format_file(f) for f in files)
