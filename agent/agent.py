"""Agent construction — builds the LangChain agent with conversation memory."""

from datetime import date

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS
from config import GEMINI_API_KEY, GEMINI_MODEL, LLM_PROVIDER, OPENAI_API_KEY


def _build_llm():
    """Build the LLM instance based on the configured provider."""
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=OPENAI_API_KEY,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0,
            google_api_key=GEMINI_API_KEY,
        )


def build_agent(
    portal_name: str,
    project_name: str,
    user_name: str,
    checkpointer: InMemorySaver,
) -> CompiledStateGraph:
    """Build a tool-calling agent with conversation memory.

    Args:
        portal_name: Display name of the selected Zoho portal.
        project_name: Display name of the selected Zoho project.
        user_name: Display name of the currently logged-in Zoho user.
        checkpointer: InMemorySaver instance that persists across Streamlit reruns.
                      Must live in st.session_state to survive script reruns.

    Returns:
        A CompiledStateGraph that handles tool calls and memory automatically.
    """
    llm = _build_llm()

    system_prompt = SYSTEM_PROMPT.format(
        portal_name=portal_name,
        project_name=project_name,
        user_name=user_name or "Unknown",
        today=date.today().isoformat(),
    )

    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
