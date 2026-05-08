"""Transcript cleaning agent.

This agent normalizes raw ASR output into a cleaner shared transcript
representation for the downstream workflow.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import invoke_with_model_fallback
from .prompts import get_cleaner_prompt
from .state import MeetingState
from .utils import sanitize_llm_text


def clean_transcript(state: MeetingState):
    """Clean the raw transcript stored in the workflow state."""
    transcript = state.get("transcript", "").strip()
    response = invoke_with_model_fallback(
        [
            SystemMessage(content=get_cleaner_prompt()),
            HumanMessage(content=f"Raw transcript:\n\n{transcript}"),
        ]
    )
    return {"cleaned_transcript": sanitize_llm_text(response.content)}


__all__ = ["clean_transcript"]
