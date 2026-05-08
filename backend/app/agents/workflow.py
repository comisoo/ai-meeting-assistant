"""
LangGraph workflow orchestration for the Meeting Minutes Assistant.

This module intentionally keeps only graph wiring and imports the
specialized agent implementations from sibling modules.
"""

from langgraph.graph import END, StateGraph

from .action_agent import extract_action_items
from .cleaner_agent import clean_transcript
from .followup_agent import generate_follow_up
from .insight_agent import generate_insights
from .state import MeetingState
from .summary_agent import generate_summary

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


__all__ = ["app_workflow", "workflow"]
