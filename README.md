# SkySec Projects Assistant

> A conversational AI assistant for **Zoho Projects** that lets teams query, view, and manage project data through natural language — with full CRUD operations, adaptive cards, OAuth 2.0, and role-based access.

Built for **SkySec Assessment No.1: Zoho Project/SAP Integration Assistant for Microsoft Teams**.

---

## What This Does

Ask questions in plain English, get structured responses:

| You Say | The Assistant Does |
|---|---|
| "List all tasks" | Fetches all tasks, renders them as adaptive cards |
| "Show my open tasks" | Filters by logged-in user + open status |
| "Tasks due this month" | Computes date range, filters by due date |
| "Show team utilisation" | Fetches time logs, renders bar chart + table |
| "Create a task 'Fix Login Bug' assigned to Dark P, high priority, due 05-15-2026" | Creates the task via Zoho API |
| "Move 'Security Audit' to In Progress" | Updates task status using custom status IDs |
| "Assign 'Code Review' to Dark P, NullSkull" | Assigns to multiple people |
| "Delete 'Setup CI/CD'" | Permanently removes the task |
| "Show milestones" | Lists project milestones and deadlines |

---

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.12+** installed
- A **Zoho Projects** account with at least one project and a few tasks
- A **Google Gemini API key** (free) from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Step 1: Clone and Install

```bash
git clone <repo-url>
cd skysecure_assignment

# Create virtual environment
python -m venv .venv

# Activate it
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Set Up Zoho OAuth

1. Go to [api-console.zoho.com](https://api-console.zoho.com/) (or `.zoho.in` for India, `.zoho.eu` for EU)
2. Click **Add Client** → **Server-based Applications**
3. Fill in:
   - **Client Name**: SkySec Projects Assistant
   - **Homepage URL**: `http://localhost:8501`
   - **Authorized Redirect URI**: `http://localhost:8501`
4. Copy the **Client ID** and **Client Secret**

### Step 3: Configure Environment

```bash
# Copy the example file
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux
```

Edit `.env` with your credentials:

```env
# Zoho OAuth (from Step 2)
ZOHO_CLIENT_ID=1000.YOUR_CLIENT_ID_HERE
ZOHO_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
ZOHO_REDIRECT_URI=http://localhost:8501
ZOHO_DOMAIN=.in                           # .com for US, .eu for Europe, etc.

# Gemini (from aistudio.google.com/apikey)
GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.1-flash-lite-preview
LLM_PROVIDER=gemini
```

> **Important**: `ZOHO_DOMAIN` must match your API Console URL domain. If your console is at `api-console.zoho.in`, set `.in`. If `api-console.zoho.com`, set `.com`.

### Step 4: Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Step 5: Connect to Zoho

1. Click **🔑 Connect to Zoho** in the sidebar
2. Authorize access in the Zoho popup
3. You're redirected back — the sidebar shows **✅ Connected to Zoho**
4. Select your **Portal** and **Project** from the dropdowns
5. Start chatting!

---

## Features

### Full Task CRUD
| Operation | How | Example |
|---|---|---|
| **Create** | Natural language | "Create task 'Write Docs' assigned to Sankalp, medium priority, due 06-01-2026" |
| **Read** | List/filter/details | "Show open tasks", "What's the status of Build REST API?" |
| **Update** | Status + priority | "Move 'Security Audit' to In Progress", "Set priority of 'Deploy' to High" |
| **Delete** | By name | "Delete 'Setup CI/CD'" |

### Data Querying
- **List all tasks** with status, owner, due date, priority
- **Filter** by status (open/closed/in progress/in review/on hold/delayed/cancelled)
- **Filter** by owner ("Show Dark P's tasks")
- **Filter** by due date ("Tasks due this month", "due next month", "due this week")
- **List all projects** in the portal
- **List team members** with roles and emails
- **Show milestones** and deadlines
- **Team utilisation** — hours logged per person with bar chart

### Adaptive Cards & Rich UI
- Task cards with status badges, owner, due date, priority
- Action buttons (Complete / Reassign) directly on cards
- Utilisation bar chart + summary table
- Quick-action sidebar buttons

### Authentication & Security
- **OAuth 2.0** — authorization code + refresh token flow
- **Multi-datacenter** — auto-detects India, US, EU, Australia, Japan, etc.
- **Auto token refresh** — seamless re-authentication when access token expires
- **RBAC** — Zoho API enforces role-based access per user's OAuth token
- **Session-only tokens** — nothing saved to disk

### Agentic Architecture
- Powered by **LangChain + LangGraph** with tool-calling
- **10 tools** for all Zoho API operations
- **Conversation memory** — remembers context within a session
- **Smart resolvers** — partial name matching for tasks and users
- Dual LLM support — **Google Gemini** (default) or **OpenAI**

---

## Project Structure

```
skysecure_assignment/
├── app.py                    # Streamlit entry point — OAuth, sidebar, chat loop
├── config.py                 # Environment variables, Zoho scopes, logging
├── requirements.txt          # Python dependencies
├── .env.example              # Template for environment configuration
├── README.md                 # This file
│
├── agent/                    # AI agent layer
│   ├── agent.py              # LangGraph agent builder (Gemini/OpenAI)
│   ├── prompts.py            # System prompt with user context injection
│   └── tools.py              # 10 LangChain tools wrapping Zoho APIs
│
├── zoho/                     # Zoho API layer
│   ├── auth.py               # OAuth URL builder, code exchange, token refresh
│   ├── client.py             # ZohoClient — typed HTTP wrapper with auto-refresh
│   └── models.py             # Pydantic models for all API responses
│
├── ui/                       # UI layer
│   ├── components.py         # Task cards, utilisation charts, rendering
│   └── styles.py             # Teams-like CSS for adaptive cards
│
└── docs/                     # Documentation
    ├── ARCHITECTURE.md       # Full system architecture, LLM flow, token economics, examples
    └── ZOHO_API_REFERENCE.md # Every Zoho API endpoint used, with params and responses
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit (adaptive card UI) |
| LLM Framework | LangChain + LangGraph (tool-calling agent with memory) |
| LLM Providers | Google Gemini (default) / OpenAI (configurable) |
| API Integration | Zoho Projects v2 REST API + v3 Time Logs API |
| Auth | OAuth 2.0 (authorization code + refresh token) |
| Models | Pydantic v2 |
| Data | Pandas (for utilisation charts) |
| Language | Python 3.12+ |

---

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `ZOHO_CLIENT_ID` | Yes | OAuth Client ID from Zoho API Console |
| `ZOHO_CLIENT_SECRET` | Yes | OAuth Client Secret |
| `ZOHO_REDIRECT_URI` | Yes | Must match API Console — default `http://localhost:8501` |
| `ZOHO_DOMAIN` | Yes | `.com`, `.in`, `.eu`, `.com.au`, `.jp`, etc. |
| `GEMINI_API_KEY` | Yes* | From Google AI Studio |
| `GEMINI_MODEL` | No | Default: `gemini-2.5-flash-lite` |
| `LLM_PROVIDER` | No | `gemini` (default) or `openai` |
| `OPENAI_API_KEY` | If OpenAI | Required only when `LLM_PROVIDER=openai` |

---

## Zoho OAuth Scopes Used

```
ZohoProjects.portals.READ
ZohoProjects.projects.READ
ZohoProjects.tasks.READ
ZohoProjects.tasks.CREATE
ZohoProjects.tasks.UPDATE
ZohoProjects.tasks.DELETE
ZohoProjects.milestones.READ
ZohoProjects.users.READ
ZohoProjects.timesheets.READ
```

> **Note on scope changes**: If you add the DELETE scope after initial OAuth setup, users must re-authorize (click "Connect to Zoho" again) to grant the new permission.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `invalid_client` error during OAuth | Check ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET in `.env`. Make sure redirect URI matches exactly. |
| `RESOURCE_EXHAUSTED` / 429 errors | Gemini free tier rate limit. Wait 1 minute and retry, or switch to a model with higher limits. |
| Tasks showing wrong filter results | Custom statuses are filtered client-side. Ensure the status name matches exactly (e.g. "In Progress" not "in-progress"). |
| "Token expired" after 1 hour | The app auto-refreshes tokens. If it persists, disconnect and reconnect via sidebar. |
| Milestones returning empty | This is expected if no milestones exist in the project. The API returns 204 No Content. |
| Time logs showing 0 entries | Team members need to have logged time in Zoho Projects first. |

---

## Assignment Compliance

### Core Requirements

| Requirement | Status | Implementation |
|---|---|---|
| Natural language querying | ✅ | Gemini/OpenAI LLM with 10 LangChain tools |
| "List all tasks" | ✅ | `list_tasks` tool → adaptive cards with progress bars |
| "Show projects due this month" | ✅ | Date range filtering with `due_after`/`due_before` |
| "Utilization of each team member" | ✅ | v3 Time Logs API → bar chart + summary table |
| Adaptive cards with actions | ✅ | Cards with Complete, Update Status, Reassign, Details, Delete buttons |
| Assign tasks from UI | ✅ | Reassign button on cards + natural language + Create Task form |
| Update task statuses from UI | ✅ | Update Status button on cards + natural language commands |
| Review team utilization from UI | ✅ | Quick action button + chart + table rendering |
| RBAC / permission models | ✅ | Zoho API enforces per-user OAuth permissions |
| OAuth 2.0 authentication | ✅ | Authorization code + refresh token + multi-datacenter |
| Secure token management | ✅ | Session-only storage, auto-refresh, no disk persistence |

### Bonus Features

| Bonus | Status | Implementation |
|---|---|---|
| Adaptive Cards & Rich UI | ✅ | Teams-style cards with status badges, progress bars, 5 action buttons |
| Multi-Platform Deployment | ✅ | Local-hosted (Streamlit), easily deployable to any Python host |
| Extensibility | ✅ | Modular architecture — separate `zoho/` client layer, swappable LLM provider |
| Create Task from UI | ✅ | Sidebar form with name, priority, due date, and assignee fields |
