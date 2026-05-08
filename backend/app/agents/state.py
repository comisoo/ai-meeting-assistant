"""Typed workflow state shared across the meeting-processing graph."""

from typing import List, TypedDict


class MeetingState(TypedDict, total=False):
    transcript: str
    template: str
    speaker_segments: List[dict]
    cleaned_transcript: str
    summary: str
    action_items: List[dict]
    insights: dict
    follow_up: str


__all__ = ["MeetingState"]
