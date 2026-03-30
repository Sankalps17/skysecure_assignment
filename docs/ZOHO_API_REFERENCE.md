# Zoho Projects API Reference — APIs Used in This System

This document lists every Zoho Projects API endpoint used by the SkySec Projects Assistant, why it's used, and how the response is consumed.

---

## Authentication

All requests use **OAuth 2.0** with Zoho's authorization code + refresh token flow.

| Step | Endpoint | Method |
|------|----------|--------|
| Authorization URL | `https://accounts.zoho{domain}/oauth/v2/auth` | Browser redirect |
| Exchange code → tokens | `https://accounts.zoho{domain}/oauth/v2/token` | POST |
| Refresh access token | `https://accounts.zoho{domain}/oauth/v2/token` | POST |

**Scopes requested:**
```
ZohoProjects.portals.READ
ZohoProjects.projects.READ
ZohoProjects.tasks.READ
ZohoProjects.tasks.CREATE
ZohoProjects.tasks.UPDATE
ZohoProjects.milestones.READ
ZohoProjects.users.READ
ZohoProjects.timesheets.READ
```

**Multi-datacenter support:** The OAuth callback includes `accounts-server` / `location` parameters. We parse these to auto-detect the user's datacenter (`.in`, `.com`, `.eu`, `.com.au`, `.jp`, etc.) so tokens are exchanged and refreshed against the correct regional endpoint.

---

## Base URLs

| API Version | Base URL | Used For |
|-------------|----------|----------|
| v2 (REST API) | `https://projectsapi.zoho{domain}/restapi` | Portals, Projects, Tasks, Users, Milestones |
| v3 | `https://projectsapi.zoho{domain}/api/v3` | Time Logs (v2 logs endpoint is deprecated) |

Where `{domain}` = `.in`, `.com`, `.eu`, etc. based on the authenticated user's datacenter.

---

## API Endpoints Used

### 1. Get Portals
```
GET /restapi/portals/
```
- **Why:** Lists all portals accessible to the user. Also returns `login_id` (ZUID) used to identify the current user.
- **Response key:** `portals[]` — each has `id_string`, `name`.
- **Used by:** Portal selector dropdown, `get_current_user_name()`.

### 2. Get Projects
```
GET /restapi/portal/{portalId}/projects/
```
- **Why:** Lists all active projects in the selected portal.
- **Response key:** `projects[]` — each has `id_string`, `name`, `status`, `owner_name`, `task_count.open`, `task_count.closed`.
- **Used by:** Project selector dropdown, `list_projects` tool.

### 3. Get Tasks (by project)
```
GET /restapi/portal/{portalId}/projects/{projectId}/tasks/
```
- **Params:**
  - `range=100` — max tasks per page
  - `status=completed|notcompleted` — API-level filter (optional)
  - `owner={userId}` — filter by assignee (optional)
- **Why:** Core task listing. Supports status and owner filtering at the API level. Custom status filtering (e.g. "in progress") is done client-side on the response.
- **Response key:** `tasks[]` — each has `id_string`, `name`, `status.name`, `status.id`, `priority`, `start_date`, `end_date`, `percent_complete`, `details.owners[]`.
- **Important:** The `status` API param only accepts `completed` or `notcompleted`. Custom statuses like "In Progress" are filtered client-side by comparing `task.status.name`.
- **Used by:** `list_tasks`, `get_task_details`, `assign_task`, `update_task_status`, `create_task` (for name resolution).

### 4. Get Task by ID
```
GET /restapi/portal/{portalId}/projects/{projectId}/tasks/{taskId}/
```
- **Why:** Fetch full details of a single task (used after updates for verification).
- **Response:** Same structure as task list but for one task.
- **Used by:** `get_task_details` tool.

### 5. Update Task
```
POST /restapi/portal/{portalId}/projects/{projectId}/tasks/{taskId}/
```
- **Params (form data):**
  - `custom_status={statusId}` — set task status by ID (not name)
  - `person_responsible={userId1},{userId2}` — assign to one or more users (comma-separated ZUIDs)
  - `priority=None|Low|Medium|High` — set priority
- **Why:** Updates task fields. Status must be set via `custom_status` (the numeric ID from task layouts), not by name.
- **Used by:** `update_task_status`, `assign_task` tools.

### 6. Create Task
```
POST /restapi/portal/{portalId}/projects/{projectId}/tasks/
```
- **Params (form data):**
  - `name` (required) — task name
  - `person_responsible={userId1},{userId2}` — assignees (optional)
  - `end_date=MM-DD-YYYY` — due date (optional)
  - `priority=None|Low|Medium|High` (optional)
  - `description` (optional)
- **Why:** Creates new tasks in the project.
- **Used by:** `create_task` tool.

### 7. Delete Task
```
DELETE /restapi/portal/{portalId}/projects/{projectId}/tasks/{taskId}/
```
- **Why:** Permanently removes a task from the project. Completes CRUD — Create, Read, Update, Delete.
- **Response:** 200 on success. The task is permanently removed.
- **Used by:** `delete_task` tool.

### 8. Get Task Layouts (Status Mapping)
```
GET /restapi/portal/{portalId}/projects/{projectId}/tasklayouts
```
- **Why:** Returns the project's task status definitions — mapping status names to IDs. Required because the Update Task API uses numeric `custom_status` IDs, not names.
- **Response key:** `layouts[].status_details[]` — each has `name`, `id`, `type` (open/closed), `is_default`, `color_code`.
- **How the mapping works:**
  1. Each status name (lowercased) → its ID (e.g., `"in progress"` → `"436611000000013001"`)
  2. Type-based fallback: if no status named "open"/"closed" exists, uses the default status of that type
- **Used by:** `update_task_status` tool (to resolve "in progress" → status ID).

### 9. Get Users
```
GET /restapi/portal/{portalId}/projects/{projectId}/users/
```
- **Why:** Lists all team members in the project. Used for name→ID resolution when assigning tasks, and to display team members.
- **Response key:** `users[]` — each has `id`, `name`, `email`, `role`.
- **Used by:** `get_users` tool, name resolution in `assign_task`, `create_task`, `list_tasks` (owner filter).

### 10. Get Milestones
```
GET /restapi/portal/{portalId}/projects/{projectId}/milestones/
```
- **Params:** `status=completed|notcompleted` (optional)
- **Why:** Lists project milestones and deadlines.
- **Response key:** `milestones[]` — each has `id`, `name`, `status`, `owner_name`, `start_date`, `end_date`, `completed_date`.
- **Note:** Returns 204 No Content if no milestones exist (handled gracefully — returns empty list).
- **Used by:** `list_milestones` tool.

### 11. Get Project Time Logs (v3 API)
```
GET /api/v3/portal/{portalId}/projects/{projectId}/timelogs
```
- **Params:**
  - `module={"type":"task"}` (required) — specifies log type
  - `view_type=projectspan` — retrieves all logs across the entire project duration
- **Why:** Fetches time logged by team members. Used for utilisation reports. The v2 `/logs/` endpoint is deprecated and returns 400, so we use the v3 endpoint.
- **Response structure:**
  ```json
  {
    "log_hours": {"total_hours": "30:00", "billable_hours": "30:00"},
    "time_logs": [
      {
        "date": "2026-03-15",
        "log_details": [
          {
            "id": "...",
            "owner": {"zpuid": "...", "name": "Sankalp S"},
            "module_detail": {"name": "Build REST API", "type": "task"},
            "log_hour": "02:00",
            "notes": "..."
          }
        ]
      }
    ]
  }
  ```
- **Used by:** `get_team_utilisation` tool → aggregates hours per person → renders bar chart.

---

## API Quirks & Design Decisions

1. **Status filtering:** The tasks API only supports `completed` / `notcompleted` as filter values. For custom statuses (In Progress, In Review, On Hold, etc.), we fetch all non-completed tasks and filter client-side by `task.status.name`.

2. **204 No Content:** Several endpoints (milestones, logs) return 204 when no data exists. Our HTTP layer handles this by returning `{}` instead of crashing on `resp.json()`.

3. **Multi-person assignment:** The `person_responsible` field accepts comma-separated ZUIDs (e.g., `"60043671330,60068377894"`) to assign a task to multiple people.

4. **Date formats:** Task due dates from the API use `MM-DD-YYYY`. The create task API also expects `MM-DD-YYYY` for `end_date`. Date-range filtering in tools uses `YYYY-MM-DD` (ISO) and converts internally.

5. **v2 vs v3:** Most endpoints work fine on v2 (`/restapi/`). Time logs is the exception — the v2 `/logs/` endpoint returns 400 for project-level queries, so we use the v3 `/api/v3/.../timelogs` endpoint which works correctly.

6. **Token refresh:** Access tokens expire after ~1 hour. Before every API call, we check `expires_at` and auto-refresh if needed. The refresh token itself doesn't expire.

7. **Role-based access:** We don't implement RBAC ourselves — the Zoho API enforces it. Each user authenticates with their own OAuth tokens, and the API only returns data they have permission to see. Admin users can update/create tasks; read-only users can only view.
