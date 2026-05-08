"""Follow-up synthesis agent.

This agent combines summary, action items, and insights into a concise
post-meeting note for execution and coordination.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import invoke_with_model_fallback
from .prompts import get_followup_prompt
from .state import MeetingState
from .utils import sanitize_llm_text


def generate_follow_up(state: MeetingState):
    """Generate a follow-up note from upstream workflow outputs."""
    summary = state.get("summary", "")
    action_items = state.get("action_items", [])
    insights = state.get("insights", {})
    template = state.get("template", "general")

    response = invoke_with_model_fallback(
        [
            SystemMessage(content=get_followup_prompt(template)),
            HumanMessage(
                content=(
                    f"Template: {template}\n\n"
                    f"Summary:\n{summary}\n\n"
                    f"Action items:\n{action_items}\n\n"
                    f"Insights:\n{insights}"
                )
            ),
        ]
    )
    return {"follow_up": sanitize_llm_text(response.content)}


__all__ = ["generate_follow_up"]
