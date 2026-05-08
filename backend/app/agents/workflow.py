"""
LangGraph workflow for the Meeting Minutes Assistant.

This version adopts a lightweight multi-agent pattern inspired by the
referenced project: one cleanup node fans out into multiple specialist
agents, and a final follow-up node merges their outputs into a practical
post-meeting deliverable.
"""

import os
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Type, TypedDict

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
    speaker_segments: List[dict]
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
    sentiment_label: str = Field(
        description="Overall emotional tone such as positive, neutral, mixed, or tense."
    )
    sentiment_score: float = Field(
        description="Confidence-like polarity score from 0 to 1, where higher means more positive."
    )
    efficiency_score: float = Field(
        description="A meeting efficiency score from 0 to 10."
    )
    efficiency_reason: str = Field(
        description="A concise explanation for why the meeting earned this efficiency score."
    )
    meeting_rhythm: List[str] = Field(
        description="Time-phase observations about how the meeting progressed, such as strong opening or late drift."
    )
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


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_speaker_segments(segments: Optional[List[dict]]) -> List[dict]:
    normalized = []
    for segment in segments or []:
        start = safe_float(segment.get("start"))
        end = safe_float(segment.get("end"), start)
        duration = max(0.0, end - start)
        normalized.append(
            {
                "speaker": segment.get("speaker") or "Unknown",
                "speaker_label": segment.get("speaker_label") or segment.get("speaker") or "Unknown",
                "text": str(segment.get("text", "")).strip(),
                "start": start,
                "end": end,
                "duration": duration,
            }
        )
    return normalized


def build_speaking_share(segments: Optional[List[dict]]) -> List[dict]:
    normalized = normalize_speaker_segments(segments)
    if not normalized:
        return []

    totals: Dict[str, Dict[str, float | str]] = {}
    total_duration = 0.0
    for segment in normalized:
        label = str(segment["speaker_label"])
        duration = safe_float(segment["duration"])
        total_duration += duration
        if label not in totals:
            totals[label] = {
                "speaker_label": label,
                "duration_seconds": 0.0,
            }
        totals[label]["duration_seconds"] = safe_float(totals[label]["duration_seconds"]) + duration

    if total_duration <= 0:
        return []

    ranked = []
    for entry in totals.values():
        duration_seconds = safe_float(entry["duration_seconds"])
        ranked.append(
            {
                "speaker_label": entry["speaker_label"],
                "duration_seconds": round(duration_seconds, 1),
                "share_ratio": round(duration_seconds / total_duration, 4),
                "share_percent": round(duration_seconds / total_duration * 100, 1),
            }
        )

    ranked.sort(key=lambda item: item["duration_seconds"], reverse=True)
    return ranked


ENGLISH_STOPWORDS = {
    "about", "after", "again", "also", "been", "being", "because", "before", "between",
    "could", "discuss", "discussion", "during", "from", "have", "into", "just", "make",
    "meeting", "minutes", "need", "next", "over", "please", "said", "should", "some",
    "team", "that", "their", "there", "these", "they", "this", "those", "today", "very",
    "want", "were", "what", "when", "with", "would", "yeah", "okay", "going", "think",
    "thanks", "thank", "project", "meeting", "agenda", "summary",
}

CHINESE_STOPWORDS = {
    "我们", "你们", "他们", "这个", "那个", "这里", "那里", "还有", "需要", "已经", "就是",
    "然后", "因为", "所以", "一个", "一下", "如果", "没有", "可以", "进行", "会议", "讨论",
    "今天", "明天", "刚才", "现在", "后面", "前面",
}


def tokenize_text_for_keywords(text: str) -> List[str]:
    english_tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
        if token.lower() not in ENGLISH_STOPWORDS
    ]
    chinese_tokens = [
        token
        for token in re.findall(r"[\u4e00-\u9fff]{2,}", text)
        if token not in CHINESE_STOPWORDS
    ]
    return english_tokens + chinese_tokens


def extract_keyword_cloud(cleaned_transcript: str, speaker_segments: Optional[List[dict]]) -> List[str]:
    docs = []
    if speaker_segments:
        docs = [segment.get("text", "") for segment in speaker_segments if segment.get("text")]
    if not docs:
        docs = [chunk.strip() for chunk in re.split(r"\n{2,}", cleaned_transcript) if chunk.strip()]
    if not docs:
        docs = [cleaned_transcript]

    tokenized_docs = [tokenize_text_for_keywords(doc) for doc in docs]
    tokenized_docs = [tokens for tokens in tokenized_docs if tokens]
    if not tokenized_docs:
        return []

    doc_count = len(tokenized_docs)
    df_counter = Counter()
    tf_counter = Counter()
    for tokens in tokenized_docs:
        tf_counter.update(tokens)
        df_counter.update(set(tokens))

    scored = []
    for token, tf in tf_counter.items():
        df = df_counter[token]
        idf = math.log((1 + doc_count) / (1 + df)) + 1
        score = tf * idf
        scored.append((token, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [token for token, _ in scored[:8]]


def serialize_speaking_share_for_prompt(speaking_share: List[dict]) -> str:
    if not speaking_share:
        return "No reliable speaker-share data available."
    return "\n".join(
        f"- {entry['speaker_label']}: {entry['share_percent']}% ({entry['duration_seconds']}s)"
        for entry in speaking_share
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
    speaker_segments = state.get("speaker_segments", [])
    speaking_share = build_speaking_share(speaker_segments)
    keyword_cloud = extract_keyword_cloud(cleaned_transcript, speaker_segments)

    sys_prompt = (
        "You are the Insight Agent for a meeting minutes assistant. Your job is to analyze "
        "meeting quality from multiple dimensions, not just summarize content. Return structured "
        "insights grounded in the transcript and any computed metadata. "
        "For sentiment_score, use a 0 to 1 scale where 1 is strongly positive and 0 is strongly negative. "
        "For efficiency_score, use a 0 to 10 scale and consider focus, decisiveness, repetition, and clarity of next steps. "
        "For meeting_rhythm, describe how the meeting evolved across phases, such as a strong opening, slow middle, or off-topic ending."
    )

    try:
        response = invoke_with_model_fallback(
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(
                    content=(
                        f"Transcript:\n\n{cleaned_transcript}\n\n"
                        f"Computed speaking share:\n{serialize_speaking_share_for_prompt(speaking_share)}\n\n"
                        f"Computed keyword candidates: {', '.join(keyword_cloud) if keyword_cloud else 'None'}"
                    )
                ),
            ],
            structured_schema=MeetingInsights,
        )
        insights = model_to_dict(response)
        insights["sentiment_score"] = round(safe_float(insights.get("sentiment_score")), 2)
        insights["efficiency_score"] = round(safe_float(insights.get("efficiency_score")), 1)
    except Exception:
        insights = {
            "sentiment_label": "Unavailable",
            "sentiment_score": 0.5,
            "efficiency_score": 0.0,
            "efficiency_reason": "Unavailable",
            "meeting_rhythm": [],
            "meeting_tone": "Unavailable",
            "key_decisions": [],
            "blockers": [],
            "next_focus": [],
        }

    insights["speaking_share"] = speaking_share
    insights["keyword_cloud"] = keyword_cloud

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
