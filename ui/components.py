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
        task: Dict with name, status, owner, due_date, priority, id, percent_complete.
        index: Position in the list (for key uniqueness).
        key_prefix: Prefix for button keys to avoid DuplicateWidgetID.
        show_actions: If False, only render the card info without buttons.
    """
    css_class = status_css_class(task["status"])
    pct = task.get("percent_complete", 0)
    try:
        pct_val = int(pct)
    except (ValueError, TypeError):
        pct_val = 0

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
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {pct_val}%"></div>
            </div>
            <div class="progress-label">{pct_val}% complete</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not show_actions:
        return

    # Direct-action buttons — no LLM round-trip needed
    _users = st.session_state.get("cached_users", [])
    _statuses = st.session_state.get("cached_statuses", {})

    btn_key = f"{key_prefix}_{task['id']}_{index}"
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("✅ Complete", key=f"{btn_key}_done", use_container_width=True):
            st.session_state["pending_action"] = {
                "type": "complete_task",
                "task_id": task["id"],
                "task_name": task["name"],
            }
            st.rerun()
    with c2:
        with st.popover("📝 Status", use_container_width=True):
            if _statuses:
                for _sname, _sid in _statuses.items():
                    if st.button(
                        _sname.title(),
                        key=f"{btn_key}_st_{_sid}",
                        use_container_width=True,
                    ):
                        st.session_state["pending_action"] = {
                            "type": "update_status",
                            "task_id": task["id"],
                            "task_name": task["name"],
                            "status_name": _sname,
                            "status_id": _sid,
                        }
                        st.rerun()
            else:
                st.caption("Loading statuses\u2026")
    with c3:
        with st.popover("👤 Reassign", use_container_width=True):
            if _users:
                for _u in _users:
                    if st.button(
                        _u["name"],
                        key=f"{btn_key}_usr_{_u['id']}",
                        use_container_width=True,
                    ):
                        st.session_state["pending_action"] = {
                            "type": "reassign_task",
                            "task_id": task["id"],
                            "task_name": task["name"],
                            "user_id": _u["id"],
                            "user_name": _u["name"],
                        }
                        st.rerun()
            else:
                st.caption("Loading team members\u2026")
    with c4:
        if st.button("🔍 Details", key=f"{btn_key}_details", use_container_width=True):
            st.session_state["pending_action"] = {
                "type": "view_details",
                "task_id": task["id"],
                "task_name": task["name"],
            }
            st.rerun()
    # Second row: delete
    _, _, _, d4 = st.columns(4)
    with d4:
        if st.button("🗑️ Delete", key=f"{btn_key}_delete", use_container_width=True):
            st.session_state["pending_action"] = {
                "type": "delete_task",
                "task_id": task["id"],
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
