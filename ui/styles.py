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
        transition: box-shadow 0.2s;
    }
    .task-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
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
        display: flex;
        flex-wrap: wrap;
        gap: 4px 16px;
        font-size: 14px;
        color: #616161;
        margin-bottom: 8px;
    }
    .task-card-body span {
        white-space: nowrap;
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
    .status-in-review { background-color: #8764B8; }
    .status-to-be-tested { background-color: #00B7C3; }
    .status-on-hold { background-color: #D83B01; }
    .status-delayed { background-color: #A4262C; }
    .status-cancelled { background-color: #8A8886; }
    .progress-bar-bg {
        background: #e1e1e1;
        border-radius: 4px;
        height: 6px;
        width: 100%;
        margin-top: 8px;
    }
    .progress-bar-fill {
        height: 6px;
        border-radius: 4px;
        background: linear-gradient(90deg, #0078D4, #00BCF2);
        transition: width 0.3s;
    }
    .progress-label {
        font-size: 11px;
        color: #8A8886;
        margin-top: 2px;
        text-align: right;
    }
</style>
"""


def status_css_class(status_name: str) -> str:
    """Map a Zoho status name to its CSS class."""
    normalized = status_name.strip().lower()
    if normalized in ("closed", "completed", "done"):
        return "status-closed"
    if "progress" in normalized:
        return "status-in-progress"
    if "review" in normalized:
        return "status-in-review"
    if "test" in normalized:
        return "status-to-be-tested"
    if "hold" in normalized:
        return "status-on-hold"
    if "delay" in normalized:
        return "status-delayed"
    if "cancel" in normalized:
        return "status-cancelled"
    return "status-open"
