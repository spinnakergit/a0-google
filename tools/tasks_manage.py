from helpers.tool import Tool, Response


class TasksManage(Tool):
    """Manage Google Tasks: create, complete, delete, or update tasks."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("tasks", self.agent):
            return Response(
                message="Tasks service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.tasks_client import TasksClient, format_task

        action = self.args.get("action", "")

        if not action:
            return Response(
                message="Error: action is required. Use: create, complete, delete, update.",
                break_loop=False,
            )

        client = TasksClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Tasks unavailable. {TasksClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            if action == "create":
                return await self._create(client, format_task)
            elif action == "complete":
                return await self._complete(client, format_task)
            elif action == "delete":
                return await self._delete(client)
            elif action == "update":
                return await self._update(client, format_task)
            else:
                return Response(
                    message=f"Unknown action '{action}'. Use: create, complete, delete, update.",
                    break_loop=False,
                )

        except Exception as e:
            return Response(
                message=f"Error managing task: {e}",
                break_loop=False,
            )

    async def _create(self, client, format_task) -> Response:
        title = self.args.get("title", "")
        notes = self.args.get("notes", "")
        due = self.args.get("due", "")
        task_list_id = self.args.get("task_list_id", "@default")

        if not title:
            return Response(
                message="Error: title is required to create a task.",
                break_loop=False,
            )

        self.set_progress(f"Creating task '{title}'...")
        result = client.create_task(
            title=title,
            notes=notes,
            due=due,
            task_list_id=task_list_id,
        )

        task_info = format_task(result)
        return Response(
            message=f"Task created successfully.\n\n{task_info}",
            break_loop=True,
        )

    async def _complete(self, client, format_task) -> Response:
        task_id = self.args.get("task_id", "")
        task_list_id = self.args.get("task_list_id", "@default")

        if not task_id:
            return Response(
                message="Error: task_id is required to complete a task.",
                break_loop=False,
            )

        self.set_progress("Marking task as completed...")
        result = client.complete_task(
            task_id=task_id,
            task_list_id=task_list_id,
        )

        task_info = format_task(result)
        return Response(
            message=f"Task completed.\n\n{task_info}",
            break_loop=True,
        )

    async def _delete(self, client) -> Response:
        task_id = self.args.get("task_id", "")
        task_list_id = self.args.get("task_list_id", "@default")

        if not task_id:
            return Response(
                message="Error: task_id is required to delete a task.",
                break_loop=False,
            )

        self.set_progress("Deleting task...")
        client.delete_task(
            task_id=task_id,
            task_list_id=task_list_id,
        )

        return Response(
            message=f"Task '{task_id}' deleted successfully.",
            break_loop=True,
        )

    async def _update(self, client, format_task) -> Response:
        task_id = self.args.get("task_id", "")
        task_list_id = self.args.get("task_list_id", "@default")

        if not task_id:
            return Response(
                message="Error: task_id is required to update a task.",
                break_loop=False,
            )

        # Collect optional update fields
        title = self.args.get("title") or None
        notes = self.args.get("notes") or None
        due = self.args.get("due") or None
        status = self.args.get("status") or None

        # Validate status if provided
        if status and status not in ("needsAction", "completed"):
            return Response(
                message=f"Error: Invalid status '{status}'. Must be 'needsAction' or 'completed'.",
                break_loop=False,
            )

        # Check that at least one field is being updated
        if not any([title, notes, due, status]):
            return Response(
                message="Error: At least one field to update is required (title, notes, due, status).",
                break_loop=False,
            )

        self.set_progress("Updating task...")
        result = client.update_task(
            task_id=task_id,
            task_list_id=task_list_id,
            title=title,
            notes=notes,
            due=due,
            status=status,
        )

        task_info = format_task(result)
        return Response(
            message=f"Task updated.\n\n{task_info}",
            break_loop=True,
        )
