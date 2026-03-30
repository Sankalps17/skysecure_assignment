"""LangChain tool definitions for Zoho Projects operations.

Each tool is self-contained: it resolves names to IDs internally so the LLM
needs only one tool call per user intent. Tools never raise exceptions — they
return descriptive error strings so the LLM can relay them naturally.
"""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from config import logger
from zoho.client import (
    ZohoAPIError,
    ZohoAuthError,
    ZohoClient,
    ZohoNotFoundError,
    ZohoRateLimitError,
)
from zoho.models import Task, User


# ── Module-level client storage (thread-safe for LangGraph) ──
# st.session_state is NOT accessible from LangGraph's thread pool.
# The client is set here by app.py before each agent invocation.

_zoho_client: ZohoClient | None = None
_last_tool_result: dict | None = None


def set_zoho_client(client: ZohoClient) -> None:
    """Set the ZohoClient instance for tools to use. Called from app.py."""
    global _zoho_client
    _zoho_client = client


def get_last_tool_result() -> dict | None:
    """Retrieve and clear the last structured tool result. Called from app.py."""
    global _last_tool_result
    result = _last_tool_result
    _last_tool_result = None
    return result


def _get_client() -> ZohoClient:
    """Retrieve the ZohoClient set via set_zoho_client()."""
    if _zoho_client is None:
        raise RuntimeError("Zoho client not initialised — connect via the sidebar first")
    return _zoho_client


def _store_tool_result(result: dict) -> None:
    """Store structured data for UI rendering (cards/charts)."""
    global _last_tool_result
    _last_tool_result = result


# ── Helpers ──


def _find_task_by_name(tasks: list[Task], name: str) -> Task | None:
    """Case-insensitive partial match on task name."""
    name_lower = name.lower()
    for t in tasks:
        if name_lower in t.name.lower():
            return t
    return None


def _find_user_by_name(users: list[User], name: str) -> User | None:
    """Case-insensitive partial match on user name."""
    name_lower = name.lower()
    for u in users:
        if name_lower in u.name.lower():
            return u
    return None


def _format_task(t: Task) -> str:
    owner_names = ", ".join(o.name for o in t.owners) or "Unassigned"
    return (
        f'"{t.name}" | Status: {t.status.name} | Owner: {owner_names} '
        f"| Due: {t.end_date or 'N/A'} | Priority: {t.priority}"
    )


def _handle_api_error(e: Exception) -> str:
    """Convert a Zoho exception into a user-friendly message."""
    logger.error("Tool error: %s", e)
    if isinstance(e, ZohoAuthError):
        return "Authentication error — your Zoho session may have expired. Please reconnect from the sidebar."
    if isinstance(e, ZohoNotFoundError):
        return f"Resource not found: {e.message}"
    if isinstance(e, ZohoRateLimitError):
        return "Zoho API rate limit reached. Please wait a moment and try again."
    if isinstance(e, ZohoAPIError):
        return f"Zoho API error: {e.message}"
    return f"Unexpected error: {e}"


def _parse_date(date_str: str) -> datetime | None:
    """Try to parse a date string in common formats (YYYY-MM-DD, MM-DD-YYYY, DD-MM-YYYY)."""
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


# ── Tools ──


@tool
def list_projects() -> str:
    """List all projects in the current Zoho Projects portal.

    Use when the user asks to see their projects or anything about what
    projects exist. Returns project names, statuses, and task counts.
    """
    try:
        client = _get_client()
        projects = client.get_projects()
        if not projects:
            return "No projects found in this portal."
        lines = [f"Found {len(projects)} project(s):"]
        for i, p in enumerate(projects, 1):
            lines.append(
                f'{i}. "{p.name}" | Status: {p.status} | Owner: {p.owner_name} '
                f"| Open tasks: {p.task_count_open} | Closed: {p.task_count_closed}"
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_api_error(e)


@tool
def list_tasks(status: str = "", owner_name: str = "", due_after: str = "", due_before: str = "") -> str:
    """List tasks in the current project, optionally filtered.

    Args:
        status: "open", "closed", a custom status name like "in progress" /
                "in review", or "" for all tasks.
        owner_name: Filter by team member name (partial match), or "" for all.
        due_after: Only include tasks due ON or AFTER this date (YYYY-MM-DD).
                   Use for "due this week/month" queries. "" to skip.
        due_before: Only include tasks due ON or BEFORE this date (YYYY-MM-DD).
                    Use for "due this week/month" queries. "" to skip.

    Returns task names, statuses, owners, priorities, and due dates.
    """
    try:
        client = _get_client()
        owner_id = ""

        # Resolve owner name → ID if provided
        if owner_name:
            users = client.get_users()
            user = _find_user_by_name(users, owner_name)
            if not user:
                available = ", ".join(u.name for u in users)
                return f'No team member matching "{owner_name}". Available: {available}'
            owner_id = user.id

        # Determine API-level vs client-side filtering
        api_status = ""
        custom_status_filter = ""
        status_lower = status.lower().strip() if status else ""
        if status_lower in ("open", "closed"):
            api_status = status_lower
            # Zoho maps open→notcompleted (returns In Progress etc. too),
            # so also apply client-side filter to match exact status name.
            custom_status_filter = status_lower
        elif status_lower:
            # Custom status (e.g. "in progress", "in review") — fetch all, filter client-side
            custom_status_filter = status_lower

        tasks = client.get_tasks(status=api_status, owner=owner_id)

        # Client-side: filter by status name
        if custom_status_filter:
            tasks = [t for t in tasks if custom_status_filter in t.status.name.lower()]

        # Client-side: filter by due date range
        if due_after or due_before:
            after_dt = _parse_date(due_after) if due_after else None
            before_dt = _parse_date(due_before) if due_before else None
            filtered = []
            for t in tasks:
                task_date = _parse_date(t.end_date) if t.end_date else None
                if task_date is None:
                    continue  # skip tasks with no due date
                if after_dt and task_date < after_dt:
                    continue
                if before_dt and task_date > before_dt:
                    continue
                filtered.append(t)
            tasks = filtered

        # Store ONLY the filtered tasks for UI card rendering
        _store_tool_result({
            "type": "task_list",
            "data": [
                {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status.name,
                    "status_color": t.status.color_code,
                    "owner": ", ".join(o.name for o in t.owners) or "Unassigned",
                    "due_date": t.end_date or "N/A",
                    "priority": t.priority,
                    "percent_complete": t.percent_complete,
                }
                for t in tasks
            ],
        })

        if not tasks:
            return "No tasks found matching your criteria."
        lines = [f"Found {len(tasks)} task(s):"]
        for i, t in enumerate(tasks, 1):
            lines.append(f"{i}. {_format_task(t)}")
        return "\n".join(lines)
    except Exception as e:
        return _handle_api_error(e)


@tool
def get_task_details(task_name: str) -> str:
    """Get detailed information about a specific task by name.

    Searches by case-insensitive partial match. Returns full details
    including ID, status, owner, priority, dates, and completion %.
    If multiple tasks match, lists them so the user can clarify.
    """
    try:
        client = _get_client()
        tasks = client.get_tasks()
        name_lower = task_name.lower()

        matches = [t for t in tasks if name_lower in t.name.lower()]
        if not matches:
            available = ", ".join(f'"{t.name}"' for t in tasks[:10])
            return f'No task found matching "{task_name}". Available tasks: {available}'

        if len(matches) > 1:
            lines = [f'Multiple tasks match "{task_name}":']
            for i, t in enumerate(matches, 1):
                lines.append(f"{i}. {_format_task(t)}")
            lines.append("Please specify which one you mean.")
            return "\n".join(lines)

        t = matches[0]
        owner_names = ", ".join(o.name for o in t.owners) or "Unassigned"
        return (
            f'Task: "{t.name}" (ID: {t.id})\n'
            f"Status: {t.status.name}\n"
            f"Owner: {owner_names}\n"
            f"Priority: {t.priority}\n"
            f"Start: {t.start_date or 'N/A'}\n"
            f"Due: {t.end_date or 'N/A'}\n"
            f"Completion: {t.percent_complete}%"
        )
    except Exception as e:
        return _handle_api_error(e)


@tool
def update_task_status(task_name: str, new_status: str = "", priority: str = "") -> str:
    """Update a task's status and/or priority.

    Resolves the task name to its ID internally — no need to look it up first.

    Args:
        task_name: The task name to find (partial match).
        new_status: New status — "closed", "open", "in progress", "in review",
                    "on hold", "delayed", "cancelled", etc. Leave empty to keep current.
        priority: New priority — "None", "Low", "Medium", "High". Leave empty to keep current.
    """
    try:
        client = _get_client()
        tasks = client.get_tasks()
        task = _find_task_by_name(tasks, task_name)

        if not task:
            available = ", ".join(f'"{t.name}"' for t in tasks[:10])
            return f'No task found matching "{task_name}". Available: {available}'

        update_fields: dict[str, str] = {}
        actions: list[str] = []

        # Handle status update
        if new_status:
            status_map = client.get_task_statuses()
            status_synonyms = {
                "complete": "closed", "completed": "closed", "done": "closed",
                "reopen": "open", "reopened": "open",
            }
            resolved = status_synonyms.get(new_status.lower(), new_status.lower())
            status_id = status_map.get(resolved, "")
            if not status_id:
                available_statuses = ", ".join(status_map.keys())
                return f'Unknown status "{new_status}". Available: {available_statuses}'
            update_fields["custom_status"] = status_id
            actions.append(f"status → {new_status}")
            logger.info("Tool update_task_status: '%s' → status '%s' (ID: %s)", task.name, new_status, status_id)

        # Handle priority update
        if priority:
            update_fields["priority"] = priority
            actions.append(f"priority → {priority}")

        if not update_fields:
            return "No changes specified. Provide a new_status and/or priority."

        result = client.update_task(task.id, **update_fields)

        # Verify the update from the response
        updated_tasks = result.get("tasks", [])
        if updated_tasks:
            actual_status = updated_tasks[0].get("status", {})
            actual_name = actual_status.get("name", "") if isinstance(actual_status, dict) else actual_status
            logger.info("Tool update_task_status: verified → status is now '%s'", actual_name)

        return f'Success: Task "{task.name}" updated — {", ".join(actions)}.'
    except Exception as e:
        return _handle_api_error(e)


@tool
def assign_task(task_name: str, assignee_names: str) -> str:
    """Assign or reassign a task to one or more team members.

    Resolves both the task name and person names to IDs internally.

    Args:
        task_name: The task to assign (partial name match).
        assignee_names: Comma-separated team member names (partial match each).
                        Example: "Sankalp, Dark P" or just "Dark P".
    """
    try:
        client = _get_client()
        tasks = client.get_tasks()
        users = client.get_users()

        task = _find_task_by_name(tasks, task_name)
        if not task:
            available = ", ".join(f'"{t.name}"' for t in tasks[:10])
            return f'No task found matching "{task_name}". Available: {available}'

        # Resolve each name to a user
        names = [n.strip() for n in assignee_names.split(",") if n.strip()]
        resolved_users = []
        for name in names:
            user = _find_user_by_name(users, name)
            if not user:
                available = ", ".join(u.name for u in users)
                return f'No team member matching "{name}". Available: {available}'
            resolved_users.append(user)

        person_ids = ",".join(u.id for u in resolved_users)
        client.update_task(task.id, person_responsible=person_ids)
        assigned_names = ", ".join(u.name for u in resolved_users)
        return f'Success: Task "{task.name}" has been assigned to {assigned_names}.'
    except Exception as e:
        return _handle_api_error(e)


@tool
def get_users() -> str:
    """List all team members in the current project.

    Use when the user asks about team members, who's on the project,
    or when you need to look up a person. Returns names, emails, and roles.
    """
    try:
        client = _get_client()
        users = client.get_users()
        if not users:
            return "No team members found in this project."
        lines = [f"Found {len(users)} team member(s):"]
        for i, u in enumerate(users, 1):
            lines.append(f"{i}. {u.name} | Email: {u.email or 'N/A'} | Role: {u.role or 'N/A'}")
        return "\n".join(lines)
    except Exception as e:
        return _handle_api_error(e)


@tool
def get_team_utilisation() -> str:
    """Get time-based utilisation for all team members in the current project.

    NO PARAMETERS NEEDED — this tool automatically uses the already-configured
    project. Just call it directly with no arguments.

    Returns total hours logged per person from time sheets.
    Use when the user asks about utilisation, workload, hours logged,
    who's busy, or team capacity.
    """
    try:
        client = _get_client()
        logs = client.get_time_logs()

        logger.info("Tool get_team_utilisation: fetched %d time log entries", len(logs))

        if not logs:
            return "No time logs found in this project yet. Team members haven't logged any hours. To see utilisation data, team members need to log time in Zoho Projects first."

        # Aggregate hours per person
        hours_by_person: dict[str, float] = {}
        for log in logs:
            hours_str = log.hours.replace(":", ".")  # "2:30" → "2.30" approx
            try:
                # Handle "H:MM" format
                if ":" in log.hours:
                    parts = log.hours.split(":")
                    hours_val = int(parts[0]) + int(parts[1]) / 60
                else:
                    hours_val = float(hours_str)
            except (ValueError, IndexError):
                hours_val = 0.0
            hours_by_person[log.owner_name] = hours_by_person.get(log.owner_name, 0.0) + hours_val

        # Store structured data for UI chart rendering
        chart_data = [
            {"name": name, "hours": round(hours, 1)}
            for name, hours in sorted(hours_by_person.items(), key=lambda x: x[1], reverse=True)
        ]
        _store_tool_result({"type": "utilisation", "data": chart_data})

        lines = ["Team utilisation (total hours logged):"]
        for entry in chart_data:
            lines.append(f"- {entry['name']}: {entry['hours']} hours")
        return "\n".join(lines)
    except Exception as e:
        return _handle_api_error(e)


@tool
def list_milestones(status: str = "") -> str:
    """List milestones in the current project.

    Args:
        status: "completed", "notcompleted", or "" for all milestones.

    Returns milestone names, statuses, owners, and due dates.
    Use when the user asks about milestones, deadlines, project phases,
    or "what's due this month".
    """
    try:
        client = _get_client()
        milestones = client.get_milestones(status=status)
        if not milestones:
            return "No milestones found in this project."
        lines = [f"Found {len(milestones)} milestone(s):"]
        for i, m in enumerate(milestones, 1):
            status_str = m.status or "N/A"
            lines.append(
                f'{i}. "{m.name}" | Status: {status_str} | Owner: {m.owner_name or "N/A"} '
                f'| Start: {m.start_date or "N/A"} | Due: {m.end_date or "N/A"}'
            )
        return "\n".join(lines)
    except Exception as e:
        return _handle_api_error(e)


@tool
def create_task(
    task_name: str,
    assignee_names: str = "",
    due_date: str = "",
    priority: str = "None",
    description: str = "",
) -> str:
    """Create a new task in the current project.

    Args:
        task_name: Name of the task to create (required).
        assignee_names: Comma-separated team member names to assign (partial match each).
                        Example: "Sankalp, Dark P". Leave empty for unassigned.
        due_date: Due date in MM-DD-YYYY format. Leave empty for no due date.
        priority: "None", "Low", "Medium", or "High".
        description: Optional task description.
    """
    try:
        client = _get_client()
        fields: dict[str, str] = {}

        if assignee_names:
            users = client.get_users()
            names = [n.strip() for n in assignee_names.split(",") if n.strip()]
            resolved_users = []
            for name in names:
                user = _find_user_by_name(users, name)
                if not user:
                    available = ", ".join(u.name for u in users)
                    return f'No team member matching "{name}". Available: {available}'
                resolved_users.append(user)
            fields["person_responsible"] = ",".join(u.id for u in resolved_users)

        if due_date:
            fields["end_date"] = due_date
        if priority and priority != "None":
            fields["priority"] = priority
        if description:
            fields["description"] = description

        result = client.create_task(task_name, **fields)
        tasks_list = result.get("tasks", [])
        if not tasks_list:
            return f'Error: Task "{task_name}" could not be created — no confirmation from Zoho.'
        task_id = tasks_list[0].get("id_string", "")
        assignee_msg = f" and assigned to {assignee_names}" if assignee_names else ""
        return f'Success: Task "{task_name}" has been created (ID: {task_id}){assignee_msg}.'
    except Exception as e:
        return _handle_api_error(e)


@tool
def delete_task(task_name: str) -> str:
    """Delete a task from the current project.

    Resolves the task name to its ID internally — no need to look it up first.
    This permanently removes the task from the project.

    Args:
        task_name: The task name to find and delete (partial match).
    """
    try:
        client = _get_client()
        tasks = client.get_tasks()
        task = _find_task_by_name(tasks, task_name)

        if not task:
            available = ", ".join(f'"{t.name}"' for t in tasks[:10])
            return f'No task found matching "{task_name}". Available: {available}'

        client.delete_task(task.id)
        return f'Success: Task "{task.name}" has been permanently deleted.'
    except Exception as e:
        return _handle_api_error(e)


# Collect all tools for the agent
ALL_TOOLS = [
    list_projects,
    list_tasks,
    get_task_details,
    update_task_status,
    assign_task,
    create_task,
    delete_task,
    get_users,
    get_team_utilisation,
    list_milestones,
]
