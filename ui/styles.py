"""CSS constants for Teams-like adaptive card styling in Streamlit."""

TEAMS_CSS = """
<style>
    .task-card {
        border: 1px solid #e1e1e1;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .task-card:hover {
        box-shadow: 0 2px 6px rgba(0,0,0,0.12);
    }
    .task-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .task-card-title {
        font-size: 16px;
        font-weight: 600;
        color: #242424;
        margin: 0;
    }
    .task-card-body {
        font-size: 14px;
        color: #616161;
    }
    .task-card-body span {
        margin-right: 12px;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        color: white;
    }
    .status-open { background-color: #0078D4; }
    .status-in-progress { background-color: #FFB900; color: #333; }
    .status-closed { background-color: #107C10; }
</style>
"""


def status_css_class(status_name: str) -> str:
    """Map a Zoho status name to its CSS class."""
    normalized = status_name.strip().lower()
    if normalized in ("closed", "completed", "done"):
        return "status-closed"
    if "progress" in normalized:
        return "status-in-progress"
    return "status-open"
