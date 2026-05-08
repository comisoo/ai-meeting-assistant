"""Prompt builders for the Meeting Minutes Assistant agents.

Keeping prompts here makes template adaptation and agent specialization
easier than embedding prompt text directly in orchestration code.
"""

NO_META_OUTPUT_RULE = (
    "Do not reveal chain-of-thought. Do not output <think> tags. "
    "Do not say things like 'The user wants me to', 'I will', or other meta commentary. "
    "Return only the requested content."
)


def get_template_instruction(template: str) -> str:
    """Return template-specific guidance shared across prompt builders."""
    template_instructions = {
        "academic": (
            "Emphasize research goals, experiment progress, findings, methodology concerns, "
            "open questions, advisor feedback, and next research steps."
        ),
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


def get_template_summary_sections(template: str) -> str:
    """Return the preferred summary section layout for a given template."""
    if template == "academic":
        return (
            "Produce Markdown with concise sections for Overview, Research Goals Discussed, "
            "Experiment or Progress Updates, Key Findings, Open Questions or Risks, Decisions, "
            "and Next Research Steps."
        )
    return "Produce Markdown with concise sections for Overview, Key Discussion Points, Decisions, and Next Steps."


def get_cleaner_prompt() -> str:
    """Prompt for transcript cleanup without summarization."""
    return (
        "You are an expert bilingual editor for English-Chinese meeting transcripts. "
        "Clean the raw transcript by fixing obvious ASR mistakes, preserving domain "
        "terms, separating speakers into readable paragraphs when possible, and "
        "keeping the original meaning intact. If a speaker change is reasonably clear, "
        "prefix the paragraph with a stable label such as 'Speaker 1:' or 'Speaker 2:'. "
        "Do not invent named speakers unless the transcript clearly contains their names. "
        f"Do not summarize. Return only the cleaned transcript. {NO_META_OUTPUT_RULE}"
    )


def get_summary_prompt(template: str) -> str:
    """Prompt for producing structured meeting minutes."""
    return (
        "You are an executive assistant writing polished meeting minutes. "
        f"Template guidance: {get_template_instruction(template)} "
        f"{get_template_summary_sections(template)} {NO_META_OUTPUT_RULE}"
    )


def get_action_prompt(template: str) -> str:
    """Prompt for structured action-item extraction."""
    extra_guidance = ""
    if template == "academic":
        extra_guidance = (
            " Pay special attention to research tasks such as running experiments, reading papers, "
            "updating slides, cleaning datasets, revising methods, writing sections, and preparing advisor follow-ups."
        )
    return (
        "Extract every actionable task discussed in the meeting. Include owner and "
        f"deadline when available. If a task is mentioned but not assigned, use 'Unassigned'. "
        f"If no deadline exists, use 'None'.{extra_guidance} {NO_META_OUTPUT_RULE}"
    )


def get_action_fallback_prompt(template: str) -> str:
    """Fallback prompt that forces pure JSON action-item output."""
    extra_guidance = ""
    if template == "academic":
        extra_guidance = (
            " Focus on research-action tasks such as experiment reruns, literature review, "
            "dataset preparation, implementation changes, advisor updates, and writing tasks."
        )
    return (
        "Extract all actionable tasks from the transcript and return valid JSON only. "
        "Use this exact schema: "
        '{"action_items":[{"task":"...","assignee":"Unassigned","deadline":"None"}]}. '
        "Do not include Markdown, code fences, commentary, or any text outside the JSON object. "
        f"{extra_guidance} {NO_META_OUTPUT_RULE}"
    )


def get_insight_prompt(template: str) -> str:
    """Prompt for meeting-quality analysis and structured insights."""
    template_guidance = ""
    if template == "academic":
        template_guidance = (
            " In academic or research meetings, interpret key_decisions as research decisions, "
            "blockers as methodological or experimental risks, and next_focus as the next research priorities. "
            "When possible, reflect whether the meeting clarified hypotheses, evidence, or next experiments."
        )
    return (
        "You are the Insight Agent for a meeting minutes assistant. Your job is to analyze "
        "meeting quality from multiple dimensions, not just summarize content. Return structured "
        "insights grounded in the transcript and any computed metadata. "
        "For sentiment_score, use a 0 to 1 scale where 1 is strongly positive and 0 is strongly negative. "
        "For efficiency_score, use a 0 to 10 scale and consider focus, decisiveness, repetition, and clarity of next steps. "
        "For meeting_rhythm, describe how the meeting evolved across phases, such as a strong opening, slow middle, or off-topic ending. "
        "The field quality_summary should read like a concise meeting-quality diagnosis, not a general summary of topics. "
        "recommended_improvements should be practical and specific to meeting quality, facilitation, focus, or next-meeting preparation. "
        f"{template_guidance} {NO_META_OUTPUT_RULE}"
    )


def get_insight_fallback_prompt(template: str) -> str:
    """Fallback prompt that forces pure JSON meeting-insight output."""
    template_guidance = ""
    if template == "academic":
        template_guidance = (
            " Interpret decisions, blockers, and next_focus through a research-meeting lens, "
            "including experiments, methods, advisor feedback, and open research questions."
        )
    return (
        "Analyze meeting quality and return valid JSON only. "
        "Use exactly this schema: "
        '{"quality_summary":"...","sentiment_label":"positive","sentiment_score":0.72,'
        '"efficiency_score":8.2,"efficiency_reason":"...",'
        '"meeting_rhythm":["..."],"meeting_tone":"aligned",'
        '"key_decisions":["..."],"blockers":["..."],"next_focus":["..."],'
        '"recommended_improvements":["..."]}. '
        "Do not include Markdown, code fences, commentary, or any text outside the JSON object. "
        f"{template_guidance} {NO_META_OUTPUT_RULE}"
    )


def get_followup_prompt(template: str) -> str:
    """Prompt for synthesizing a follow-up note from workflow outputs."""
    section_guidance = "Immediate Follow-up, Recommended Owner Check-ins, and Suggested Next Meeting Agenda."
    extra_guidance = ""
    if template == "academic":
        section_guidance = (
            "Immediate Follow-up, Research Checkpoints, and Suggested Next Research Meeting Agenda."
        )
        extra_guidance = (
            " Emphasize experiment execution, advisor alignment, evidence gaps, and preparation for the next research review."
        )
    return (
        "You are preparing a practical post-meeting follow-up note. Based on the "
        "meeting summary, extracted action items, and insights, write a concise "
        f"Markdown follow-up with these sections: {section_guidance} "
        f"Keep it actionable.{extra_guidance} {NO_META_OUTPUT_RULE}"
    )


def get_meeting_qa_prompt() -> str:
    """Prompt for answering questions grounded in a single meeting record."""
    return (
        "You are a meeting assistant answering questions about one specific meeting record. "
        "Use only the provided meeting data. Prefer the cleaned transcript and speaker timeline as evidence when needed. "
        "If the record does not contain enough information, say so clearly instead of guessing. "
        "Answer in concise Markdown with direct, practical wording. "
        f"{NO_META_OUTPUT_RULE}"
    )


__all__ = [
    "NO_META_OUTPUT_RULE",
    "get_action_fallback_prompt",
    "get_action_prompt",
    "get_cleaner_prompt",
    "get_followup_prompt",
    "get_insight_fallback_prompt",
    "get_insight_prompt",
    "get_meeting_qa_prompt",
    "get_summary_prompt",
    "get_template_instruction",
]
