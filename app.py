"""SkySec Projects Assistant — Streamlit entry point.

Handles session state initialisation, OAuth callback, sidebar controls,
chat rendering, and agent invocation. Run with: streamlit run app.py
"""

import uuid

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.agent import build_agent
from agent.tools import get_last_tool_result, set_zoho_client
from config import ZOHO_DOMAIN, LLM_PROVIDER, GEMINI_MODEL, logger
from ui.components import inject_css, render_task_cards, render_utilisation_chart
from zoho.auth import build_auth_url, exchange_code
from zoho.client import ZohoClient
from zoho.models import ZohoTokens

# ── Zoho datacenter detection ──

# Maps the "location" callback param to Zoho domain suffix.
# See https://www.zoho.com/accounts/protocol/oauth/multi-dc.html
_LOCATION_TO_DOMAIN: dict[str, str] = {
    "us": ".com", "eu": ".eu", "in": ".in",
    "au": ".com.au", "jp": ".jp", "ca": "cloud.ca",
    "sa": ".sa", "uk": ".uk",
}


def _detect_zoho_domain(params: dict) -> str:
    """Detect Zoho domain suffix from OAuth callback params.

    Zoho includes 'accounts-server' and/or 'location' in the redirect URL
    to indicate which datacenter the user belongs to.
    """
    # Primary: parse from accounts-server URL (e.g. "https://accounts.zoho.in")
    accounts_server = params.get("accounts-server", "")
    if accounts_server:
        from urllib.parse import urlparse
        host = urlparse(accounts_server).hostname or ""
        prefix = "accounts.zoho"
        if host.startswith(prefix):
            return host[len(prefix):]  # e.g. ".in", ".com", "cloud.ca"

    # Fallback: use location param (e.g. "in", "us", "eu")
    location = params.get("location", "")
    if location:
        return _LOCATION_TO_DOMAIN.get(location, "")

    return ""

# ── Page config ──

st.set_page_config(page_title="SkySec Projects Assistant", page_icon="🔒", layout="wide")
inject_css()

# ── Session state defaults ──

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "checkpointer" not in st.session_state:
    st.session_state["checkpointer"] = InMemorySaver()


# ── OAuth callback handling ──


def _handle_oauth_callback() -> None:
    """Check query params for an OAuth code and exchange it for tokens.

    Reads 'accounts-server' / 'location' from the callback to auto-detect
    the correct Zoho datacenter, then exchanges the code for tokens using
    the right accounts URL.
    """
    params = st.query_params
    code = params.get("code")
    if not code or "zoho_tokens" in st.session_state:
        return

    # Auto-detect the user's Zoho datacenter from callback params
    detected_domain = _detect_zoho_domain(params)
    if detected_domain:
        st.session_state["zoho_domain"] = detected_domain
        logger.info("Detected Zoho datacenter domain: %s", detected_domain)

    domain = st.session_state.get("zoho_domain", ZOHO_DOMAIN)

    # Clear URL params immediately to prevent retry loops on failure
    # (codes are single-use and expire in ~2 minutes)
    st.query_params.clear()

    try:
        tokens = exchange_code(code, domain=domain)
        st.session_state["zoho_tokens"] = tokens.model_dump()
        logger.info("OAuth tokens obtained successfully")
        st.rerun()
    except Exception as e:
        st.session_state["_oauth_error"] = str(e)
        logger.error("OAuth callback failed: %s", e)


_handle_oauth_callback()


# ── Helper: build or retrieve ZohoClient ──


def _get_or_build_client() -> ZohoClient | None:
    """Build a ZohoClient from session state tokens, or return None if not connected."""
    tokens_dict = st.session_state.get("zoho_tokens")
    if not tokens_dict:
        return None

    domain = st.session_state.get("zoho_domain", ZOHO_DOMAIN)
    tokens = ZohoTokens(**tokens_dict)
    client = ZohoClient(
        tokens=tokens,
        portal_id=st.session_state.get("portal_id", ""),
        project_id=st.session_state.get("project_id", ""),
        domain=domain,
    )
    # Keep tokens in sync after potential refresh
    st.session_state["zoho_tokens"] = client.tokens.model_dump()
    st.session_state["zoho_client"] = client
    return client


# ── Sidebar ──


def _render_sidebar() -> None:
    """Render the sidebar: connection status, portal/project selectors, quick actions."""
    with st.sidebar:
        st.header("🔗 Zoho Connection")

        # Show any OAuth error from a previous attempt
        if oauth_error := st.session_state.pop("_oauth_error", None):
            st.error(f"OAuth error: {oauth_error}")

        if not st.session_state.get("zoho_tokens"):
            st.link_button("🔑 Connect to Zoho", build_auth_url())
            st.caption("Click to authorise access to your Zoho Projects")
            return

        st.success("✅ Connected to Zoho")
        if st.button("Disconnect"):
            for key in ["zoho_tokens", "portal_id", "project_id", "portal_name",
                        "project_name", "zoho_client", "portals_cache", "projects_cache",
                        "zoho_domain", "user_name"]:
                st.session_state.pop(key, None)
            st.rerun()

        client = _get_or_build_client()
        if not client:
            return

        # Portal selector
        if "portals_cache" not in st.session_state:
            try:
                st.session_state["portals_cache"] = client.get_portals()
            except Exception as e:
                st.error(f"Failed to load portals: {e}")
                return

        portals = st.session_state["portals_cache"]
        if not portals:
            st.warning("No portals found.")
            return

        portal_names = [p.name for p in portals]
        selected_portal = st.selectbox("Portal", portal_names)
        idx = portal_names.index(selected_portal)
        st.session_state["portal_id"] = portals[idx].id
        st.session_state["portal_name"] = portals[idx].name
        client.portal_id = portals[idx].id

        # Project selector
        cache_key = f"projects_cache_{portals[idx].id}"
        if cache_key not in st.session_state:
            try:
                st.session_state[cache_key] = client.get_projects()
            except Exception as e:
                st.error(f"Failed to load projects: {e}")
                return

        projects = st.session_state[cache_key]
        if not projects:
            st.warning("No projects found in this portal.")
            return

        project_names = [p.name for p in projects]
        selected_project = st.selectbox("Project", project_names)
        pidx = project_names.index(selected_project)
        st.session_state["project_id"] = projects[pidx].id
        st.session_state["project_name"] = projects[pidx].name
        client.project_id = projects[pidx].id

        # Detect current user name (cached)
        if "user_name" not in st.session_state:
            try:
                detected_name = client.get_current_user_name()
                st.session_state["user_name"] = detected_name
                logger.info("Detected current user: %s", detected_name)
            except Exception:
                st.session_state["user_name"] = ""

        if st.session_state.get("user_name"):
            st.caption(f"👤 Logged in as: {st.session_state['user_name']}")

        # LLM info
        provider_display = "OpenAI (gpt-4o-mini)" if LLM_PROVIDER == "openai" else f"Gemini ({GEMINI_MODEL})"
        st.caption(f"🤖 LLM: {provider_display}")

        # Quick actions
        st.divider()
        st.subheader("⚡ Quick Actions")
        if st.button("📋 My Tasks"):
            st.session_state["pending_input"] = "Show my open tasks"
            st.rerun()
        if st.button("📊 Team Utilisation"):
            st.session_state["pending_input"] = "Show team utilisation"
            st.rerun()


_render_sidebar()


# ── Handle pending action from card buttons ──


def _handle_pending_action() -> None:
    """Convert a pending card-button action into a chat message."""
    action = st.session_state.pop("pending_action", None)
    if not action:
        return

    if action["type"] == "complete_task":
        prompt = f"Mark task '{action['task_name']}' as complete"
    elif action["type"] == "reassign_task":
        prompt = f"Who should I reassign '{action['task_name']}' to?"
        # For reassign, just add as user message — agent will ask for the name
    else:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.session_state["pending_input"] = prompt
    st.session_state["_msg_pre_added"] = True


_handle_pending_action()


# ── Main chat area ──

st.title("🔒 SkySec Projects Assistant")

# Guard: require connection + project selection
if not st.session_state.get("zoho_tokens"):
    st.info("👈 Connect to Zoho using the sidebar to get started.")
    st.stop()

if not st.session_state.get("project_id"):
    st.info("👈 Select a portal and project from the sidebar.")
    st.stop()


# ── Render chat history ──

for _msg_idx, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Re-render structured data if stored with the message.
        # History cards have no action buttons (prevents stale data + key collisions).
        if msg.get("card_data"):
            render_task_cards(msg["card_data"], key_prefix=f"hist_{_msg_idx}", show_actions=False)
        elif msg.get("chart_data"):
            render_utilisation_chart(msg["chart_data"])


# ── Chat input ──

# Pick up prefilled input from quick actions or pending actions
pending_input = st.session_state.pop("pending_input", None)
prompt = st.chat_input("Ask about your projects...")

# Use pending input if no direct chat input
if not prompt and pending_input:
    prompt = pending_input

if prompt:
    # Add user message (unless already added by _handle_pending_action)
    pre_added = st.session_state.pop("_msg_pre_added", False)
    if not pre_added:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # Build agent fresh each rerun (cheap — objects only, memory survives in session_state)
    try:
        agent = build_agent(
            portal_name=st.session_state.get("portal_name", ""),
            project_name=st.session_state.get("project_name", ""),
            user_name=st.session_state.get("user_name", ""),
            checkpointer=st.session_state["checkpointer"],
        )
    except Exception as e:
        st.error(f"Failed to initialise agent: {e}")
        logger.error("Agent build error: %s", e)
        st.stop()

    # Ensure tools have access to the ZohoClient (thread-safe, module-level)
    client = _get_or_build_client()
    if client:
        set_zoho_client(client)

    # Invoke with spinner
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = agent.invoke(
                    {"messages": [HumanMessage(content=prompt)]},
                    config={"configurable": {"thread_id": st.session_state["session_id"]}},
                )
                raw_content = response["messages"][-1].content
                # Gemini may return content as a list of blocks instead of a string
                if isinstance(raw_content, list):
                    output = "\n".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in raw_content
                    )
                else:
                    output = raw_content
            except Exception as e:
                error_str = str(e)
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    output = (
                        "⏳ **Rate limit reached.** The Gemini API free tier limits requests "
                        "per minute and per day. Please wait a minute and try again, or switch "
                        "to a model with higher limits (see `.env` → `GEMINI_MODEL`)."
                    )
                else:
                    output = f"Something went wrong: {e}"
                logger.error("Agent error: %s", e)

        # Sync tokens back after potential refresh during tool calls
        if client:
            st.session_state["zoho_tokens"] = client.tokens.model_dump()

        # Check for structured tool data (cards/charts)
        tool_result = get_last_tool_result()

        if tool_result and tool_result.get("data"):
            st.markdown(output)
            if tool_result["type"] == "task_list":
                _cur_msg_idx = len(st.session_state["messages"])
                render_task_cards(tool_result["data"], key_prefix=f"cur_{_cur_msg_idx}")
            elif tool_result["type"] == "utilisation":
                render_utilisation_chart(tool_result["data"])
        else:
            st.markdown(output)

        # Store message for history rendering
        msg_data: dict = {"role": "assistant", "content": output}
        if tool_result and tool_result.get("data"):
            if tool_result["type"] == "task_list":
                msg_data["card_data"] = tool_result["data"]
            elif tool_result["type"] == "utilisation":
                msg_data["chart_data"] = tool_result["data"]

        st.session_state["messages"].append(msg_data)
