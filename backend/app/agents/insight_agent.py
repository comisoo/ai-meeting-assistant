"""Meeting insight and quality-analysis agent.

This module combines LLM-based meeting diagnostics with heuristic
analytics such as speaking share and keyword extraction.
"""

import math
import re
from collections import Counter
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .llm import invoke_with_model_fallback
from .prompts import get_insight_fallback_prompt, get_insight_prompt
from .state import MeetingState
from .utils import (
    dedupe_preserve_order,
    extract_json_payload,
    model_to_dict,
    normalize_phrase_list,
    normalize_short_text,
    safe_float,
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


def generate_insights(state: MeetingState):
    """Generate structured meeting insights and derived quality metrics."""
    cleaned_transcript = state.get("cleaned_transcript", "")
    speaker_segments = state.get("speaker_segments", [])
    template = state.get("template", "general")
    speaking_share = build_speaking_share(speaker_segments)
    keyword_cloud = extract_keyword_cloud(cleaned_transcript, speaker_segments)
    participation_balance = classify_participation_balance(speaking_share)

    try:
        response = invoke_with_model_fallback(
            [
                SystemMessage(content=get_insight_prompt(template)),
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
        try:
            response = invoke_with_model_fallback(
                [
                    SystemMessage(content=get_insight_fallback_prompt(template)),
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


__all__ = [
    "MeetingInsights",
    "build_speaking_share",
    "classify_participation_balance",
    "extract_keyword_cloud",
    "generate_insights",
    "normalize_speaker_segments",
    "serialize_speaking_share_for_prompt",
    "tokenize_text_for_keywords",
]
