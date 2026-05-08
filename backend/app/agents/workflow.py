"""
LangGraph workflow for the Meeting Minutes Assistant.

This version adopts a lightweight multi-agent pattern inspired by the
referenced project: one cleanup node fans out into multiple specialist
agents, and a final follow-up node merges their outputs into a practical
post-meeting deliverable.
"""

import json
import os
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Type, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


DEFAULT_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
DEFAULT_PRIMARY_MODEL = os.environ.get("MINIMAX_PRIMARY_MODEL", "MiniMax-M2.7")
DEFAULT_FALLBACK_MODELS = [
    model.strip()
    for model in os.environ.get(
        "MINIMAX_FALLBACK_MODELS",
        "MiniMax-M2.7-highspeed,MiniMax-M2.5,MiniMax-M2.5-highspeed",
    ).split(",")
    if model.strip()
]
NO_META_OUTPUT_RULE = (
    "Do not reveal chain-of-thought. Do not output <think> tags. "
    "Do not say things like 'The user wants me to', 'I will', or other meta commentary. "
    "Return only the requested content."
)


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
    quality_summary: str = Field(
        description="A concise 2-3 sentence diagnostic summary of the meeting quality."
    )
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
    recommended_improvements: List[str] = Field(
        description="Concrete suggestions for improving the next meeting."
    )


def build_meeting_qa_context(meeting: dict) -> str:
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


def classify_participation_balance(speaking_share: List[dict]) -> str:
    if not speaking_share:
        return "unavailable"

    top_share = safe_float(speaking_share[0].get("share_percent"))
    if top_share >= 60:
        return "highly concentrated"
    if top_share >= 45:
        return "moderately concentrated"
    return "fairly balanced"


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
    "今天", "明天", "刚才", "现在", "后面", "前面", "觉得", "问题", "内容", "相关", "方面",
}


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def normalize_phrase_list(items: object, limit: int = 5) -> List[str]:
    if not isinstance(items, list):
        return []

    phrases = []
    for item in items:
        text = sanitize_llm_text(str(item)).strip(" -\n\t")
        if text:
            phrases.append(text)
    return dedupe_preserve_order(phrases)[:limit]


def normalize_short_text(value: object, fallback: str = "Unavailable") -> str:
    text = sanitize_llm_text(str(value or "")).strip()
    return text or fallback


def tokenize_text_for_keywords(text: str) -> List[str]:
    english_tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
        if token.lower() not in ENGLISH_STOPWORDS
    ]

    chinese_tokens: List[str] = []
    try:
        import jieba  # type: ignore

        for token in jieba.cut(text):
            normalized = token.strip().lower()
            if len(normalized) < 2 or len(normalized) > 8:
                continue
            if normalized in CHINESE_STOPWORDS:
                continue
            if re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9_-]+", normalized):
                chinese_tokens.append(normalized)
    except Exception:
        fragments = re.split(r"[，。！？；：、“”‘’（）()\[\]\s,.;:!?]+", text)
        for fragment in fragments:
            normalized = fragment.strip().lower()
            if len(normalized) < 2 or len(normalized) > 8:
                continue
            if normalized in CHINESE_STOPWORDS:
                continue
            if re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9_-]+", normalized):
                chinese_tokens.append(normalized)

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
    ranked = [token for token, _ in scored if len(token.strip()) <= 8]
    return dedupe_preserve_order(ranked)[:8]


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


def sanitize_llm_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"```(?:json|markdown|md)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(
        r"^\s*(the user wants me to|the user asked me to|i will|i should|i need to)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_json_payload(text: str) -> Optional[dict]:
    cleaned = sanitize_llm_text(text)
    if not cleaned:
        return None

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def create_llm(model_name: str, structured_schema: Optional[Type[BaseModel]] = None):
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key or api_key == "your_minimax_api_key_here":
        raise RuntimeError("MINIMAX_API_KEY is missing or invalid.")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        temperature=0.2,
    )
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
    raise RuntimeError("No MiniMax model candidates were configured.")


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
        f"Do not summarize. Return only the cleaned transcript. {NO_META_OUTPUT_RULE}"
    )

    response = invoke_with_model_fallback(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Raw transcript:\n\n{transcript}"),
        ]
    )
    return {"cleaned_transcript": sanitize_llm_text(response.content)}


def generate_summary(state: MeetingState):
    cleaned_transcript = state.get("cleaned_transcript", "")
    template = state.get("template", "general")

    sys_prompt = (
        "You are an executive assistant writing polished meeting minutes. "
        f"Template guidance: {get_template_instruction(template)} "
        "Produce Markdown with concise sections for Overview, Key Discussion Points, "
        f"Decisions, and Next Steps. {NO_META_OUTPUT_RULE}"
    )

    response = invoke_with_model_fallback(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Cleaned transcript:\n\n{cleaned_transcript}"),
        ]
    )
    return {"summary": sanitize_llm_text(response.content)}


def extract_action_items(state: MeetingState):
    cleaned_transcript = state.get("cleaned_transcript", "")

    sys_prompt = (
        "Extract every actionable task discussed in the meeting. Include owner and "
        "deadline when available. If a task is mentioned but not assigned, use "
        f"'Unassigned'. If no deadline exists, use 'None'. {NO_META_OUTPUT_RULE}"
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

    if not items:
        fallback_prompt = (
            "Extract all actionable tasks from the transcript and return valid JSON only. "
            "Use this exact schema: "
            '{"action_items":[{"task":"...","assignee":"Unassigned","deadline":"None"}]}. '
            "Do not include Markdown, code fences, commentary, or any text outside the JSON object. "
            f"{NO_META_OUTPUT_RULE}"
        )
        try:
            response = invoke_with_model_fallback(
                [
                    SystemMessage(content=fallback_prompt),
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

    return {"action_items": items}


def generate_insights(state: MeetingState):
    cleaned_transcript = state.get("cleaned_transcript", "")
    speaker_segments = state.get("speaker_segments", [])
    speaking_share = build_speaking_share(speaker_segments)
    keyword_cloud = extract_keyword_cloud(cleaned_transcript, speaker_segments)
    participation_balance = classify_participation_balance(speaking_share)

    sys_prompt = (
        "You are the Insight Agent for a meeting minutes assistant. Your job is to analyze "
        "meeting quality from multiple dimensions, not just summarize content. Return structured "
        "insights grounded in the transcript and any computed metadata. "
        "For sentiment_score, use a 0 to 1 scale where 1 is strongly positive and 0 is strongly negative. "
        "For efficiency_score, use a 0 to 10 scale and consider focus, decisiveness, repetition, and clarity of next steps. "
        "For meeting_rhythm, describe how the meeting evolved across phases, such as a strong opening, slow middle, or off-topic ending. "
        "The field quality_summary should read like a concise meeting-quality diagnosis, not a general summary of topics. "
        "recommended_improvements should be practical and specific to meeting quality, facilitation, focus, or next-meeting preparation. "
        f"{NO_META_OUTPUT_RULE}"
    )

    try:
        response = invoke_with_model_fallback(
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(
                    content=(
                        f"Transcript:\n\n{cleaned_transcript}\n\n"
                        f"Computed speaking share:\n{serialize_speaking_share_for_prompt(speaking_share)}\n\n"
                        f"Computed keyword candidates: {', '.join(keyword_cloud) if keyword_cloud else 'None'}\n\n"
                        f"Participation balance heuristic: {participation_balance}"
                    )
                ),
            ],
            structured_schema=MeetingInsights,
        )
        insights = model_to_dict(response)
    except Exception:
        insights = {}

    if not insights:
        fallback_prompt = (
            "Analyze meeting quality and return valid JSON only. "
            "Use exactly this schema: "
            '{"quality_summary":"...","sentiment_label":"positive","sentiment_score":0.72,'
            '"efficiency_score":8.2,"efficiency_reason":"...",'
            '"meeting_rhythm":["..."],"meeting_tone":"aligned",'
            '"key_decisions":["..."],"blockers":["..."],"next_focus":["..."],'
            '"recommended_improvements":["..."]}. '
            "Do not include Markdown, code fences, commentary, or any text outside the JSON object. "
            f"{NO_META_OUTPUT_RULE}"
        )
        try:
            response = invoke_with_model_fallback(
                [
                    SystemMessage(content=fallback_prompt),
                    HumanMessage(
                        content=(
                            f"Transcript:\n\n{cleaned_transcript}\n\n"
                            f"Computed speaking share:\n{serialize_speaking_share_for_prompt(speaking_share)}\n\n"
                            f"Computed keyword candidates: {', '.join(keyword_cloud) if keyword_cloud else 'None'}\n\n"
                            f"Participation balance heuristic: {participation_balance}"
                        )
                    ),
                ]
            )
            insights = extract_json_payload(response.content) or {}
        except Exception:
            insights = {}

    if not insights:
        insights = {
            "quality_summary": "Meeting quality summary unavailable.",
            "sentiment_label": "Unavailable",
            "sentiment_score": 0.5,
            "efficiency_score": 0.0,
            "efficiency_reason": "Unavailable",
            "meeting_rhythm": [],
            "meeting_tone": "Unavailable",
            "key_decisions": [],
            "blockers": [],
            "next_focus": [],
            "recommended_improvements": [],
        }

    insights["quality_summary"] = normalize_short_text(
        insights.get("quality_summary"),
        "Meeting quality summary unavailable.",
    )
    insights["sentiment_label"] = normalize_short_text(insights.get("sentiment_label"))
    insights["efficiency_reason"] = normalize_short_text(insights.get("efficiency_reason"))
    insights["meeting_tone"] = normalize_short_text(insights.get("meeting_tone"))
    insights["sentiment_score"] = round(
        min(1.0, max(0.0, safe_float(insights.get("sentiment_score"), 0.5))),
        2,
    )
    insights["efficiency_score"] = round(
        min(10.0, max(0.0, safe_float(insights.get("efficiency_score"), 0.0))),
        1,
    )
    insights["meeting_rhythm"] = normalize_phrase_list(insights.get("meeting_rhythm"), limit=4)
    insights["key_decisions"] = normalize_phrase_list(insights.get("key_decisions"), limit=5)
    insights["blockers"] = normalize_phrase_list(insights.get("blockers"), limit=5)
    insights["next_focus"] = normalize_phrase_list(insights.get("next_focus"), limit=5)
    insights["recommended_improvements"] = normalize_phrase_list(
        insights.get("recommended_improvements"),
        limit=4,
    )

    insights["speaking_share"] = speaking_share
    insights["keyword_cloud"] = keyword_cloud
    insights["participation_balance"] = participation_balance

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
        f"Owner Check-ins, and Suggested Next Meeting Agenda. Keep it actionable. {NO_META_OUTPUT_RULE}"
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
    return {"follow_up": sanitize_llm_text(response.content)}


def answer_meeting_question(meeting: dict, question: str) -> str:
    context = build_meeting_qa_context(meeting)
    sys_prompt = (
        "You are a meeting assistant answering questions about one specific meeting record. "
        "Use only the provided meeting data. Prefer the cleaned transcript and speaker timeline as evidence when needed. "
        "If the record does not contain enough information, say so clearly instead of guessing. "
        "Answer in concise Markdown with direct, practical wording. "
        f"{NO_META_OUTPUT_RULE}"
    )
    response = invoke_with_model_fallback(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(
                content=(
                    f"Meeting record:\n\n{context}\n\n"
                    f"User question: {question.strip()}"
                )
            ),
        ]
    )
    return sanitize_llm_text(response.content)


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
