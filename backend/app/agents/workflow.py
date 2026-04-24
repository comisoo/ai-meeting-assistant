"""
LangGraph workflow for the Meeting Minutes Assistant.

This version adopts a lightweight multi-agent pattern inspired by the
referenced project: one cleanup node fans out into multiple specialist
agents, and a final follow-up node merges their outputs into a practical
post-meeting deliverable.
"""

import os
from typing import List, Optional, Type, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


DEFAULT_PRIMARY_MODEL = os.environ.get("GROQ_PRIMARY_MODEL", "llama-3.1-8b-instant")
DEFAULT_FALLBACK_MODELS = [
    model.strip()
    for model in os.environ.get("GROQ_FALLBACK_MODELS", "llama-3.3-70b-versatile").split(",")
    if model.strip()
]


class MeetingState(TypedDict, total=False):
    transcript: str
    template: str
    cleaned_transcript: str
    summary: str
    action_items: List[dict]
    insights: dict
    follow_up: str


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


class MeetingInsights(BaseModel):
    meeting_tone: str = Field(
        description="Overall tone, such as aligned, tense, exploratory, or mixed."
    )
    key_decisions: List[str] = Field(description="Important decisions made during the meeting.")
    blockers: List[str] = Field(
        description="Risks, blockers, or unresolved issues raised in the meeting."
    )
    next_focus: List[str] = Field(
        description="The most important topics to focus on next."
    )


def get_model_candidates() -> List[str]:
    models = [DEFAULT_PRIMARY_MODEL, *DEFAULT_FALLBACK_MODELS]
    deduped = []
    for model in models:
        if model and model not in deduped:
            deduped.append(model)
    return deduped


def create_llm(model_name: str, structured_schema: Optional[Type[BaseModel]] = None):
    llm = ChatGroq(model=model_name, temperature=0.2)
    if structured_schema is not None:
        return llm.with_structured_output(structured_schema)
    return llm


def is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "rate limit" in message or "rate_limit_exceeded" in message or "error code: 429" in message


def invoke_with_model_fallback(messages, structured_schema: Optional[Type[BaseModel]] = None):
    last_exception = None

    for model_name in get_model_candidates():
        try:
            llm = create_llm(model_name, structured_schema=structured_schema)
            return llm.invoke(messages)
        except Exception as exc:
            last_exception = exc
            if not is_rate_limit_error(exc):
                raise

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("No Groq model candidates were configured.")


def model_to_dict(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def get_template_instruction(template: str) -> str:
    template_instructions = {
        "daily": (
            "Prioritize progress since the last update, today's plan, blockers, "
            "dependencies, and immediate owners."
        ),
        "brainstorm": (
            "Highlight promising ideas, tradeoffs, open questions, and which ideas "
            "should be explored further."
        ),
        "client": (
            "Emphasize client requirements, feedback, commitments, risks, and agreed "
            "next steps."
        ),
        "general": (
            "Provide a comprehensive overview of topics discussed, decisions made, "
            "unresolved issues, and follow-up tasks."
        ),
    }
    return template_instructions.get(template, template_instructions["general"])


def clean_transcript(state: MeetingState):
    transcript = state.get("transcript", "").strip()

    sys_prompt = (
        "You are an expert bilingual editor for English-Chinese meeting transcripts. "
        "Clean the raw transcript by fixing obvious ASR mistakes, preserving domain "
        "terms, separating speakers into readable paragraphs when possible, and "
        "keeping the original meaning intact. If a speaker change is reasonably clear, "
        "prefix the paragraph with a stable label such as 'Speaker 1:' or 'Speaker 2:'. "
        "Do not invent named speakers unless the transcript clearly contains their names. "
        "Do not summarize. Return only the cleaned transcript."
    )

    response = invoke_with_model_fallback(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Raw transcript:\n\n{transcript}"),
        ]
    )
    return {"cleaned_transcript": response.content}


def generate_summary(state: MeetingState):
    cleaned_transcript = state.get("cleaned_transcript", "")
    template = state.get("template", "general")

    sys_prompt = (
        "You are an executive assistant writing polished meeting minutes. "
        f"Template guidance: {get_template_instruction(template)} "
        "Produce Markdown with concise sections for Overview, Key Discussion Points, "
        "Decisions, and Next Steps."
    )

    response = invoke_with_model_fallback(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Cleaned transcript:\n\n{cleaned_transcript}"),
        ]
    )
    return {"summary": response.content}


def extract_action_items(state: MeetingState):
    cleaned_transcript = state.get("cleaned_transcript", "")

    sys_prompt = (
        "Extract every actionable task discussed in the meeting. Include owner and "
        "deadline when available. If a task is mentioned but not assigned, use "
        "'Unassigned'. If no deadline exists, use 'None'."
    )

    try:
        response = invoke_with_model_fallback(
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"Transcript:\n\n{cleaned_transcript}"),
            ],
            structured_schema=ActionItemsExtraction,
        )
        items = [model_to_dict(item) for item in response.action_items]
    except Exception:
        items = []

    return {"action_items": items}


def generate_insights(state: MeetingState):
    cleaned_transcript = state.get("cleaned_transcript", "")

    sys_prompt = (
        "Analyze the meeting and capture higher-level signals. Extract the overall "
        "meeting tone, the most important decisions, current blockers or risks, and "
        "what the team should focus on next. Keep insights grounded in the transcript."
    )

    try:
        response = invoke_with_model_fallback(
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"Transcript:\n\n{cleaned_transcript}"),
            ],
            structured_schema=MeetingInsights,
        )
        insights = model_to_dict(response)
    except Exception:
        insights = {
            "meeting_tone": "Unavailable",
            "key_decisions": [],
            "blockers": [],
            "next_focus": [],
        }

    return {"insights": insights}


def generate_follow_up(state: MeetingState):
    summary = state.get("summary", "")
    action_items = state.get("action_items", [])
    insights = state.get("insights", {})
    template = state.get("template", "general")

    sys_prompt = (
        "You are preparing a practical post-meeting follow-up note. Based on the "
        "meeting summary, extracted action items, and insights, write a concise "
        "Markdown follow-up with these sections: Immediate Follow-up, Recommended "
        "Owner Check-ins, and Suggested Next Meeting Agenda. Keep it actionable."
    )

    response = invoke_with_model_fallback(
        [
            SystemMessage(content=sys_prompt),
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
    return {"follow_up": response.content}


workflow = StateGraph(MeetingState)

workflow.add_node("cleaner", clean_transcript)
workflow.add_node("summarizer", generate_summary)
workflow.add_node("action_item_extractor", extract_action_items)
workflow.add_node("insight_generator", generate_insights)
workflow.add_node("follow_up_writer", generate_follow_up)

workflow.set_entry_point("cleaner")

workflow.add_edge("cleaner", "summarizer")
workflow.add_edge("cleaner", "action_item_extractor")
workflow.add_edge("cleaner", "insight_generator")

workflow.add_edge("summarizer", "follow_up_writer")
workflow.add_edge("action_item_extractor", "follow_up_writer")
workflow.add_edge("insight_generator", "follow_up_writer")

workflow.add_edge("follow_up_writer", END)

app_workflow = workflow.compile()
