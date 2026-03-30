"""UI components — task cards, utilisation charts, and structured data rendering."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.styles import TEAMS_CSS, status_css_class


def inject_css() -> None:
    """Inject Teams-like CSS into the Streamlit page (call once at app start)."""
    st.markdown(TEAMS_CSS, unsafe_allow_html=True)


def render_task_card(task: dict, index: int, key_prefix: str = "", show_actions: bool = True) -> None:
    """Render a single task as a Teams-style adaptive card.

    Args:
        task: Dict with name, status, owner, due_date, priority, id.
        index: Position in the list (for key uniqueness).
        key_prefix: Prefix for button keys to avoid DuplicateWidgetID.
        show_actions: If False, only render the card info without buttons.
    """
    css_class = status_css_class(task["status"])
    st.markdown(
        f"""
        <div class="task-card">
            <div class="task-card-header">
                <p class="task-card-title">📋 {task["name"]}</p>
                <span class="status-badge {css_class}">{task["status"]}</span>
            </div>
            <div class="task-card-body">
                <span>👤 {task["owner"]}</span>
                <span>📅 Due: {task["due_date"]}</span>
                <span>🔥 {task["priority"]}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not show_actions:
        return
    # Action buttons row
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("✅ Complete", key=f"{key_prefix}_complete_{task['id']}_{index}"):
            st.session_state["pending_action"] = {
                "type": "complete_task",
                "task_name": task["name"],
            }
            st.rerun()
    with col2:
        if st.button("👤 Reassign", key=f"{key_prefix}_reassign_{task['id']}_{index}"):
            st.session_state["pending_action"] = {
                "type": "reassign_task",
                "task_name": task["name"],
            }
            st.rerun()


def render_task_cards(tasks: list[dict], key_prefix: str = "", show_actions: bool = True) -> None:
    """Render a list of tasks as adaptive cards."""
    for i, task in enumerate(tasks):
        render_task_card(task, i, key_prefix=key_prefix, show_actions=show_actions)


def render_utilisation_chart(data: list[dict]) -> None:
    """Render team utilisation as a bar chart with a summary table."""
    if not data:
        st.info("No utilisation data available.")
        return

    df = pd.DataFrame(data)
    st.subheader("📊 Team Utilisation")
    st.bar_chart(df.set_index("name")["hours"])
    st.dataframe(
        df.rename(columns={"name": "Team Member", "hours": "Hours Logged"}),
        hide_index=True,
        width="stretch",
    )
