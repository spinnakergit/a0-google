from helpers.tool import Tool, Response


class TasksList(Tool):
    """List Google Tasks lists or tasks within a specific list."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("tasks", self.agent):
            return Response(
                message="Tasks service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.tasks_client import TasksClient, format_task_list

        action = self.args.get("action", "tasks")
        task_list_id = self.args.get("task_list_id", "@default")
        show_completed = self.args.get("show_completed", "")
        limit = int(self.args.get("limit", "50"))

        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        # Parse show_completed as boolean
        show_completed_bool = str(show_completed).lower() in ("true", "1", "yes")

        client = TasksClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Tasks unavailable. {TasksClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            if action == "lists":
                self.set_progress("Fetching task lists...")
                task_lists = client.list_task_lists(max_results=limit)

                if not task_lists:
                    return Response(message="No task lists found.", break_loop=False)

                lines = [f"Google Task Lists ({len(task_lists)}):"]
                for tl in task_lists:
                    title = tl.get("title", "Untitled")
                    tl_id = tl.get("id", "")
                    updated = tl.get("updated", "")[:19].replace("T", " ") if tl.get("updated") else ""
                    entry = f"\n**{title}**\n  ID: {tl_id}"
                    if updated:
                        entry += f"\n  Updated: {updated}"
                    lines.append(entry)

                return Response(message="\n".join(lines), break_loop=False)

            elif action == "tasks":
                self.set_progress("Fetching tasks...")
                tasks = client.list_tasks(
                    task_list_id=task_list_id,
                    max_results=limit,
                    show_completed=show_completed_bool,
                )

                completed_note = " (including completed)" if show_completed_bool else ""
                if not tasks:
                    return Response(
                        message=f"No tasks found in list '{task_list_id}'{completed_note}.",
                        break_loop=False,
                    )

                header = f"Tasks in '{task_list_id}'{completed_note} ({len(tasks)}):"
                result = format_task_list(tasks)
                return Response(message=f"{header}\n\n{result}", break_loop=False)

            else:
                return Response(
                    message=f"Unknown action '{action}'. Use 'lists' to show all task lists, "
                            f"or 'tasks' to show tasks in a specific list.",
                    break_loop=False,
                )

        except Exception as e:
            return Response(
                message=f"Error listing tasks: {e}",
                break_loop=False,
            )
