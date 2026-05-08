"""Action-item extraction agent.

This module owns the action-item schema plus the structured-output and
JSON-fallback extraction flow for executable meeting tasks.
"""

import re
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .llm import invoke_with_model_fallback
from .prompts import get_action_fallback_prompt, get_action_prompt
from .state import MeetingState
from .utils import extract_json_payload, model_to_dict


class ActionItem(BaseModel):
    task: str = Field(description="The concrete action item or task to be completed.")
    assignee: str = Field(
        description="The person responsible for the task, or 'Unassigned' if not stated."
    )
    deadline: str = Field(
        description="The due date, time, or milestone for the task, or 'None' if not stated."
    )


class ActionItemsExtraction(BaseModel):
    action_items: List[ActionItem] = Field(
        description="All actionable tasks explicitly or implicitly agreed in the meeting."
    )


def classify_academic_action_category(task: str) -> str:
    """Assign a lightweight research-task category from task text."""
    normalized = str(task or "").strip().lower()
    if not normalized:
        return "Research Task"

    category_rules = [
        ("Experiment", [r"\bexperiment\b", r"\brerun\b", r"\bablation\b", r"\bevaluate\b", r"\bbenchmark\b"]),
        ("Reading", [r"\bread\b", r"\bpaper\b", r"\bliterature\b", r"\bsurvey\b", r"\breview\b"]),
        ("Writing", [r"\bwrite\b", r"\bdraft\b", r"\brevise\b", r"\breport\b", r"\bsection\b", r"\bmanuscript\b"]),
        ("Coding", [r"\bimplement\b", r"\bcode\b", r"\bdebug\b", r"\btrain\b", r"\bscript\b", r"\brefactor\b"]),
        ("Data Prep", [r"\bdataset\b", r"\bdata\b", r"\bclean\b", r"\bcollect\b", r"\bpreprocess\b", r"\blabel\b"]),
        ("Presentation", [r"\bslide\b", r"\bpresentation\b", r"\bdemo\b", r"\bmeeting prep\b"]),
    ]

    for category, patterns in category_rules:
        for pattern in patterns:
            if re.search(pattern, normalized):
                return category
    return "Research Task"


def extract_action_items(state: MeetingState):
    """Extract action items from the cleaned transcript in workflow state."""
    cleaned_transcript = state.get("cleaned_transcript", "")
    template = state.get("template", "general")

    try:
        response = invoke_with_model_fallback(
            [
                SystemMessage(content=get_action_prompt(template)),
                HumanMessage(content=f"Transcript:\n\n{cleaned_transcript}"),
            ],
            structured_schema=ActionItemsExtraction,
        )
        items = [model_to_dict(item) for item in response.action_items]
    except Exception:
        items = []

    if not items:
        try:
            response = invoke_with_model_fallback(
                [
                    SystemMessage(content=get_action_fallback_prompt(template)),
                    HumanMessage(content=f"Transcript:\n\n{cleaned_transcript}"),
                ]
            )
            payload = extract_json_payload(response.content) or {}
            raw_items = payload.get("action_items", [])
            if isinstance(raw_items, list):
                items = [
                    {
                        "task": str(item.get("task", "")).strip(),
                        "assignee": str(item.get("assignee", "Unassigned")).strip() or "Unassigned",
                        "deadline": str(item.get("deadline", "None")).strip() or "None",
                    }
                    for item in raw_items
                    if isinstance(item, dict) and str(item.get("task", "")).strip()
                ]
        except Exception:
            items = items or []

    if template == "academic":
        for item in items:
            item["category"] = classify_academic_action_category(item.get("task", ""))

    return {"action_items": items}


__all__ = [
    "ActionItem",
    "ActionItemsExtraction",
    "classify_academic_action_category",
    "extract_action_items",
]
