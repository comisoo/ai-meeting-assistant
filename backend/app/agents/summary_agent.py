"""Meeting-summary generation agent.

This agent turns the cleaned transcript into structured meeting minutes
using the currently selected meeting template.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import invoke_with_model_fallback
from .prompts import get_summary_prompt
from .state import MeetingState
from .utils import sanitize_llm_text


def generate_summary(state: MeetingState):
    """Generate a structured summary from the cleaned transcript."""
    cleaned_transcript = state.get("cleaned_transcript", "")
    template = state.get("template", "general")
    response = invoke_with_model_fallback(
        [
            SystemMessage(content=get_summary_prompt(template)),
            HumanMessage(content=f"Cleaned transcript:\n\n{cleaned_transcript}"),
        ]
    )
    return {"summary": sanitize_llm_text(response.content)}


__all__ = ["generate_summary"]
