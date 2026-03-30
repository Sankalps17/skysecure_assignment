"""Zoho Projects API client — authenticated HTTP requests with auto-refresh.

Uses v2 REST API (/restapi/) for tasks, projects, users, milestones and
the v3 API (/api/v3/) for time logs (the v2 logs endpoint is deprecated).
"""

import time

import requests

from config import logger
from zoho.auth import refresh_access_token
from zoho.models import (
    Milestone,
    Portal,
    Project,
    Task,
    TaskOwner,
    TaskStatus,
    TimeLog,
    User,
    ZohoTokens,
)


# ── Exceptions ──


class ZohoAPIError(Exception):
    """Base exception for Zoho API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Zoho API {status_code}: {message}")


class ZohoAuthError(ZohoAPIError):
    """401 — token expired or invalid."""


class ZohoNotFoundError(ZohoAPIError):
    """404 — resource not found."""


class ZohoRateLimitError(ZohoAPIError):
    """429 — rate limit exceeded."""


# ── Client ──


class ZohoClient:
    """Thin wrapper around the Zoho Projects REST API.

    Handles auth headers, automatic token refresh, and response parsing.
    All methods return Pydantic models — never raw dicts.
    """

    def __init__(
        self,
        tokens: ZohoTokens,
        portal_id: str = "",
        project_id: str = "",
        domain: str = ".com",
    ):
        self.tokens = tokens
        self.portal_id = portal_id
        self.project_id = project_id
        self.base_url = f"https://projectsapi.zoho{domain}/restapi"
        self._domain = domain

    # ── HTTP plumbing ──

    def _ensure_fresh_token(self) -> None:
        """Refresh the access token if it has expired."""
        if time.time() >= self.tokens.expires_at:
            self.tokens = refresh_access_token(self.tokens.refresh_token, domain=self._domain)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Zoho-oauthtoken {self.tokens.access_token}"}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated API request, raising typed exceptions on errors."""
        self._ensure_fresh_token()
        url = f"{self.base_url}{path}"
        logger.info("Zoho API → %s %s", method, path)

        resp = requests.request(
            method, url, headers=self._headers(), timeout=30, **kwargs
        )

        logger.info("Zoho API ← %s %s [%d] (%dms)",
                     method, path, resp.status_code,
                     int(resp.elapsed.total_seconds() * 1000))

        if resp.status_code == 401:
            raise ZohoAuthError(401, "Token expired or invalid")
        if resp.status_code == 404:
            raise ZohoNotFoundError(404, f"Resource not found: {path}")
        if resp.status_code == 429:
            raise ZohoRateLimitError(429, "Rate limit exceeded — wait and retry")
        if resp.status_code >= 400:
            logger.error("Zoho API error: %s %s → %d: %s", method, path, resp.status_code, resp.text[:300])
            raise ZohoAPIError(resp.status_code, resp.text[:200])

        # 204 No Content — valid response, no body to parse
        if resp.status_code == 204 or not resp.text.strip():
            return {}

        return resp.json()

    def _get(self, path: str, **params) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, **data) -> dict:
        return self._request("POST", path, data=data)

    # ── Portals & Projects ──

    def get_portals(self) -> list[Portal]:
        """Fetch all portals accessible to the authenticated user."""
        data = self._get("/portals/")
        return [
            Portal(id=p["id_string"], name=p["name"])
            for p in data.get("portals", [])
        ]

    def get_projects(self) -> list[Project]:
        """Fetch all active projects in the current portal."""
        data = self._get(f"/portal/{self.portal_id}/projects/")
        return [
            Project(
                id=p["id_string"],
                name=p["name"],
                status=p.get("status", "active"),
                owner_name=p.get("owner_name", ""),
                task_count_open=p.get("task_count", {}).get("open", 0),
                task_count_closed=p.get("task_count", {}).get("closed", 0),
            )
            for p in data.get("projects", [])
        ]

    # ── Tasks ──

    def get_tasks(self, status: str = "", owner: str = "") -> list[Task]:
        """Fetch tasks in the current project with optional status/owner filters."""
        params: dict = {"range": "100"}
        if status:
            # Zoho All Tasks API uses "completed" / "notcompleted", not "open"/"closed"
            status_map = {"open": "notcompleted", "closed": "completed"}
            params["status"] = status_map.get(status.lower(), status)
        if owner:
            params["owner"] = owner

        path = f"/portal/{self.portal_id}/projects/{self.project_id}/tasks/"
        data = self._get(path, **params)
        return [self._parse_task(t) for t in data.get("tasks", [])]

    def get_task_by_id(self, task_id: str) -> Task:
        """Fetch a single task by its ID."""
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/tasks/{task_id}/"
        data = self._get(path)
        raw = data.get("tasks", [data])
        return self._parse_task(raw[0] if isinstance(raw, list) else raw)

    def update_task(self, task_id: str, **fields: str) -> dict:
        """Update a task's fields (status, persons, name, etc.)."""
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/tasks/{task_id}/"
        logger.info("Updating task %s with fields: %s", task_id, fields)
        result = self._post(path, **fields)
        # Log the updated task status from response for verification
        tasks = result.get("tasks", [])
        if tasks:
            updated = tasks[0]
            status_info = updated.get("status", {})
            status_name = status_info.get("name", "") if isinstance(status_info, dict) else status_info
            logger.info("Task %s updated → status: %s, completed: %s",
                        task_id, status_name, updated.get("completed"))
        return result

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by its ID. Returns True on success."""
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/tasks/{task_id}/"
        logger.info("Deleting task %s", task_id)
        self._request("DELETE", path)
        return True

    def _parse_task(self, t: dict) -> Task:
        """Convert a raw Zoho task dict into a Task model."""
        owners = [
            TaskOwner(id=o["id"], name=o["name"])
            for o in t.get("details", {}).get("owners", [])
        ]
        status_raw = t.get("status", {})
        if isinstance(status_raw, str):
            status = TaskStatus(name=status_raw, id="")
        else:
            status = TaskStatus(
                name=status_raw.get("name", ""),
                id=str(status_raw.get("id", "")),
                color_code=status_raw.get("color_code", ""),
            )
        return Task(
            id=t.get("id_string", str(t.get("id", ""))),
            name=t["name"],
            status=status,
            priority=t.get("priority", "None"),
            start_date=t.get("start_date", ""),
            end_date=t.get("end_date", ""),
            owners=owners,
            percent_complete=t.get("percent_complete", "0"),
        )

    # ── Users ──

    def get_users(self) -> list[User]:
        """Fetch all team members in the current project."""
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/users/"
        data = self._get(path)
        return [
            User(
                id=u.get("id", ""),
                name=u["name"],
                email=u.get("email", ""),
                role=u.get("role", ""),
            )
            for u in data.get("users", [])
        ]

    def get_current_user_name(self) -> str:
        """Detect the current authenticated user's name.

        Uses the login_id from the portals endpoint to match against
        the project's user list, so each user sees their own name.
        """
        login_id = ""
        try:
            data = self._get("/portals/")
            login_id = str(data.get("login_id", ""))
            logger.info("Zoho login_id from portals: %s", login_id)
        except Exception:
            pass

        try:
            users = self.get_users()
            # Match by login_id (numeric ZUID)
            if login_id:
                for u in users:
                    if str(u.id) == login_id:
                        return u.name
            # Fallback: portal owner role
            for u in users:
                if u.role and "admin" in u.role.lower():
                    return u.name
            if users:
                return users[0].name
        except Exception:
            pass
        return ""

    # ── Task Statuses ──

    def get_task_statuses(self) -> dict[str, str]:
        """Fetch task layout to get status name→ID mapping.

        Returns a dict mapping lowercased status names to IDs.
        Type-based fallbacks ("open"/"closed") are only added when
        no status with that exact name exists in the layout.
        """
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/tasklayouts"
        data = self._get(path)

        status_map: dict[str, str] = {}
        type_defaults: dict[str, str] = {}  # type → best default status ID
        type_fallbacks: dict[str, str] = {}  # type → first status ID (if no default)

        layouts = data.get("layouts", [data])
        for layout in layouts:
            statuses_raw = layout.get("status_details", [])
            logger.info(
                "Tasklayout statuses (%d): %s",
                len(statuses_raw),
                [(s.get("name"), s.get("id"), s.get("type"), s.get("is_default")) for s in statuses_raw],
            )
            for status in statuses_raw:
                stype = status.get("type", "").lower()
                sid = str(status.get("id", ""))
                sname = status.get("name", "")
                is_default = status.get("is_default", False)

                # Always map by exact name (lowercase)
                if sname and sid:
                    status_map[sname.lower()] = sid

                # For type-based fallback, prefer the status whose name
                # matches the type (e.g. "Closed" for type "closed").
                if stype and sid and is_default:
                    if stype not in type_defaults or sname.lower() == stype:
                        type_defaults[stype] = sid
                elif stype and sid and stype not in type_fallbacks:
                    type_fallbacks[stype] = sid

        # Only add type-based mapping if no exact name match already exists.
        # This prevents e.g. "Cancelled" (type=closed) from overwriting "Closed".
        for stype in ("open", "closed"):
            if stype not in status_map:
                if stype in type_defaults:
                    status_map[stype] = type_defaults[stype]
                elif stype in type_fallbacks:
                    status_map[stype] = type_fallbacks[stype]

        logger.info("Task status mapping: %s", {k: v for k, v in status_map.items()})
        return status_map

    # ── Time Logs ──

    def get_time_logs(self) -> list[TimeLog]:
        """Fetch time log entries for the current project via the Zoho v3 API.

        Uses the /api/v3/ timelogs endpoint with view_type=projectspan to
        retrieve all task-related time logs across the entire project span.
        """
        self._ensure_fresh_token()

        url = (
            f"https://projectsapi.zoho{self._domain}/api/v3"
            f"/portal/{self.portal_id}/projects/{self.project_id}/timelogs"
        )
        params = {
            "module": '{"type":"task"}',
            "view_type": "projectspan",
        }

        logger.info("Fetching time logs: GET %s  params=%s", url, params)
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        logger.info("Time logs response: %d (%dms)", resp.status_code,
                     int(resp.elapsed.total_seconds() * 1000))

        if resp.status_code >= 400:
            logger.error("Time logs error: %d — %s", resp.status_code, resp.text[:500])
            return []

        data = resp.json()
        result: list[TimeLog] = []
        for date_block in data.get("time_logs", []):
            log_date = date_block.get("date", "")
            for entry in date_block.get("log_details", []):
                owner = entry.get("owner", {})
                module = entry.get("module_detail", {})
                result.append(
                    TimeLog(
                        id=str(entry.get("id", "")),
                        task_name=module.get("name", ""),
                        owner_name=owner.get("name", ""),
                        owner_id=str(owner.get("zpuid", "")),
                        hours=entry.get("log_hour", "0"),
                        notes=entry.get("notes", ""),
                        date=log_date,
                    )
                )

        logger.info("Parsed %d time log entries", len(result))
        return result

    # ── Task Creation ──

    def create_task(self, name: str, **fields: str) -> dict:
        """Create a new task in the current project.

        Args:
            name: Task name (required).
            **fields: Optional fields — person_responsible, start_date,
                      end_date (MM-DD-YYYY), priority, description.
        """
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/tasks/"
        logger.info("Creating task '%s' with fields: %s", name, fields)
        return self._post(path, name=name, **fields)

    # ── Milestones ──

    def get_milestones(self, status: str = "") -> list[Milestone]:
        """Fetch milestones in the current project.

        Args:
            status: "completed", "notcompleted", or "" for all.
        """
        path = f"/portal/{self.portal_id}/projects/{self.project_id}/milestones/"
        params: dict = {}
        if status:
            params["status"] = status
        data = self._get(path, **params)
        return [
            Milestone(
                id=str(m.get("id", "")),
                name=m.get("name", ""),
                status=m.get("status", ""),
                owner_name=m.get("owner_name", ""),
                start_date=m.get("start_date", ""),
                end_date=m.get("end_date", ""),
                completed_date=m.get("completed_date", ""),
            )
            for m in data.get("milestones", [])
        ]