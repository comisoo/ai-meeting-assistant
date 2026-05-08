"""Meeting-scoped Q&A agent.

This module answers user questions grounded only in one selected meeting
record and its derived outputs.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import invoke_with_model_fallback
from .prompts import get_meeting_qa_prompt
from .utils import sanitize_llm_text


def build_meeting_qa_context(meeting: dict) -> str:
    """Assemble a bounded context string for one meeting record."""
    transcript = (
        meeting.get("cleaned_transcript")
        or meeting.get("speaker_aware_transcript")
        or meeting.get("transcript")
        or ""
    ).strip()
    transcript_excerpt = transcript[:12000]

    action_items = meeting.get("action_items", [])
    action_block = (
        "\n".join(
            f"- Task: {item.get('task', '')} | Owner: {item.get('assignee', 'Unassigned')} | Deadline: {item.get('deadline', 'None')}"
            for item in action_items
        )
        if action_items
        else "None"
    )

    insights = meeting.get("insights", {}) or {}
    insights_block = json.dumps(insights, ensure_ascii=False, indent=2) if insights else "None"

    speaker_segments = meeting.get("speaker_segments", []) or []
    speaker_excerpt = "\n".join(
        f"[{segment.get('start', 0):.1f}-{segment.get('end', 0):.1f}] {segment.get('speaker_label') or segment.get('speaker')}: {segment.get('text', '')}"
        for segment in speaker_segments[:12]
    ) or "None"

    return (
        f"Meeting filename: {meeting.get('filename', 'Unknown')}\n"
        f"Template: {meeting.get('template', 'general')}\n"
        f"Created at: {meeting.get('created_at', 'Unknown')}\n\n"
        f"Summary:\n{meeting.get('summary', '') or 'None'}\n\n"
        f"Action items:\n{action_block}\n\n"
        f"Insights:\n{insights_block}\n\n"
        f"Follow-up:\n{meeting.get('follow_up', '') or 'None'}\n\n"
        f"Speaker timeline excerpt:\n{speaker_excerpt}\n\n"
        f"Cleaned transcript excerpt:\n{transcript_excerpt or 'None'}"
    )


def answer_meeting_question(meeting: dict, question: str) -> str:
    """Answer a user question using only the supplied meeting record."""
    context = build_meeting_qa_context(meeting)
    response = invoke_with_model_fallback(
        [
            SystemMessage(content=get_meeting_qa_prompt()),
            HumanMessage(
                content=(
                    f"Meeting record:\n\n{context}\n\n"
                    f"User question: {question.strip()}"
                )
            ),
        ]
    )
    return sanitize_llm_text(response.content)


__all__ = ["answer_meeting_question", "build_meeting_qa_context"]
