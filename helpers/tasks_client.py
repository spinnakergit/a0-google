"""Google Tasks API client wrapper.

Handles task listing, creation, completion, and deletion.
Auth is delegated to google_auth.
"""

import logging
from typing import Optional

from usr.plugins.google.helpers.google_auth import (
    get_google_config, build_service, GoogleAuthError,
)

logger = logging.getLogger("google.tasks_client")


class TasksClient:
    """Google Tasks API wrapper."""

    last_error: str = ""

    def __init__(self, service):
        self._service = service

    @classmethod
    def from_config(cls, agent=None) -> Optional["TasksClient"]:
        """Build a TasksClient from plugin config. Returns None if unavailable."""
        config = get_google_config(agent)
        try:
            service = build_service("tasks", config)
            cls.last_error = ""
            return cls(service=service)
        except GoogleAuthError as e:
            cls.last_error = f"Auth: {e}"
            logger.warning("[google-plugin] TasksClient auth failed: %s", e)
            return None
        except Exception as e:
            cls.last_error = f"{type(e).__name__}: {e}"
            logger.warning("[google-plugin] TasksClient build failed: %s: %s", type(e).__name__, e)
            return None

    def list_task_lists(self, max_results: int = 20) -> list:
        """List all task lists."""
        result = self._service.tasklists().list(maxResults=max_results).execute()
        return result.get("items", [])

    def list_tasks(
        self,
        task_list_id: str = "@default",
        max_results: int = 50,
        show_completed: bool = False,
    ) -> list:
        """List tasks in a task list."""
        result = self._service.tasks().list(
            tasklist=task_list_id,
            maxResults=max_results,
            showCompleted=show_completed,
        ).execute()
        return result.get("items", [])

    def create_task(
        self,
        title: str,
        notes: str = "",
        due: str = "",
        task_list_id: str = "@default",
    ) -> dict:
        """Create a new task."""
        task = {"title": title}
        if notes:
            task["notes"] = notes
        if due:
            # Tasks API expects RFC 3339 date
            if "T" not in due:
                due += "T00:00:00.000Z"
            task["due"] = due

        return self._service.tasks().insert(
            tasklist=task_list_id, body=task
        ).execute()

    def complete_task(self, task_id: str, task_list_id: str = "@default") -> dict:
        """Mark a task as completed."""
        task = self._service.tasks().get(
            tasklist=task_list_id, task=task_id
        ).execute()
        task["status"] = "completed"
        return self._service.tasks().update(
            tasklist=task_list_id, task=task_id, body=task
        ).execute()

    def delete_task(self, task_id: str, task_list_id: str = "@default") -> None:
        """Delete a task."""
        self._service.tasks().delete(
            tasklist=task_list_id, task=task_id
        ).execute()

    def update_task(
        self,
        task_id: str,
        task_list_id: str = "@default",
        title: Optional[str] = None,
        notes: Optional[str] = None,
        due: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """Update a task. Only provided fields are changed."""
        task = self._service.tasks().get(
            tasklist=task_list_id, task=task_id
        ).execute()

        if title is not None:
            task["title"] = title
        if notes is not None:
            task["notes"] = notes
        if due is not None:
            if "T" not in due:
                due += "T00:00:00.000Z"
            task["due"] = due
        if status is not None:
            task["status"] = status

        return self._service.tasks().update(
            tasklist=task_list_id, task=task_id, body=task
        ).execute()


def format_task(task: dict) -> str:
    """Format a single task for display."""
    title = task.get("title", "Untitled")
    status = task.get("status", "needsAction")
    check = "[x]" if status == "completed" else "[ ]"

    parts = [f"{check} **{title}**"]

    if task.get("notes"):
        notes = task["notes"]
        if len(notes) > 200:
            notes = notes[:200] + "..."
        parts.append(f"  Notes: {notes}")

    if task.get("due"):
        due = task["due"][:10]
        parts.append(f"  Due: {due}")

    parts.append(f"  ID: {task.get('id', '')}")
    return "\n".join(parts)


def format_task_list(tasks: list) -> str:
    """Format a list of tasks for display."""
    if not tasks:
        return "No tasks found."
    return "\n\n".join(format_task(t) for t in tasks)
