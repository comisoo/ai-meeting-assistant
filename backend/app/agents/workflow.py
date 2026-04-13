"""
LangGraph workflow for the Meeting Minutes Assistant using Groq LPUs.
"""
import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

# -----------------
# State Definition
# -----------------
class MeetingState(TypedDict):
    transcript: str
    template: str # e.g., 'daily', 'brainstorm', 'client', 'general'
    cleaned_transcript: str
    summary: str
    action_items: List[dict] # Will store action items as dicts

# -----------------
# Pydantic Schemas
# -----------------
class ActionItem(BaseModel):
    task: str = Field(description="The specific action item or task to be completed.")
    assignee: str = Field(description="The person assigned to the task, or 'Unassigned' if not mentioned.")
    deadline: str = Field(description="The deadline for the task, or 'None' if not specified.")

class ActionItemsExtraction(BaseModel):
    action_items: List[ActionItem] = Field(description="List of all extracted action items.")

# -----------------
# Helper: Get LLM
# -----------------
def get_llm():
    # llama-3.3-70b-versatile is excellent for complex instruction following and extraction
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

# -----------------
# Agent Nodes
# -----------------
def process_transcription(state: MeetingState):
    """
    Cleans the Whisper transcript, fixing code-switching and formatting it nicely.
    """
    transcript = state.get("transcript", "")
    llm = get_llm()
    
    sys_prompt = (
        "You are an expert bilingual editor (English and Chinese). "
        "Your job is to take a raw audio transcript which may contain code-switching "
        "(mixed English and Chinese) and inaccurate voice-to-text artifacts. "
        "Clean up the text, correct any obvious jargon mistakes, and format it clearly "
        "while preserving the original meaning. Do not summarize yet, just output the cleaned transcript."
    )
    
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Raw Transcript:\n\n{transcript}")
    ]
    
    response = llm.invoke(messages)
    return {"cleaned_transcript": response.content}

def generate_summary(state: MeetingState):
    """
    Generates a structured summary based on the chosen meeting template.
    """
    cleaned_transcript = state.get("cleaned_transcript", "")
    template = state.get("template", "general")
    llm = get_llm()
    
    template_instructions = {
        "daily": "Focus on what was done yesterday, what will be done today, and any blockers.",
        "brainstorm": "Focus on the newly generated ideas, pros/cons discussed, and potential directions.",
        "client": "Focus on client requirements, feedback, pain points, and agreed next steps.",
        "general": "Provide a comprehensive overview of the main topics discussed and key decisions made."
    }
    
    instruction = template_instructions.get(template, template_instructions["general"])
    
    sys_prompt = (
        f"You are an executive assistant. Generate a highly structured, professional meeting summary. "
        f"Template specific instruction: {instruction}\n\n"
        f"Format your response in Markdown."
    )
    
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Cleaned Transcript:\n\n{cleaned_transcript}")
    ]
    
    response = llm.invoke(messages)
    return {"summary": response.content}

def extract_action_items(state: MeetingState):
    """
    Extracts action items using structured output formatting.
    """
    cleaned_transcript = state.get("cleaned_transcript", "")
    llm = get_llm().with_structured_output(ActionItemsExtraction)
    
    sys_prompt = (
        "Analyze the provided meeting transcript and extract all actionable items, tasks, and assignments. "
        "You must extract 100% of the tasks discussed. If none exist, return an empty list."
    )
    
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Transcript:\n\n{cleaned_transcript}")
    ]
    
    # We use invoke which returns the Pydantic object
    try:
        response = llm.invoke(messages)
        # Convert objects to dicts for state
        items = [item.dict() for item in response.action_items]
    except Exception as e:
        items = [] # Fallback
        
    return {"action_items": items}

# -----------------
# Graph Compilation
# -----------------
workflow = StateGraph(MeetingState)

# Add nodes
workflow.add_node("transcriber", process_transcription)
workflow.add_node("summarizer", generate_summary)
workflow.add_node("action_item_extractor", extract_action_items)

# Add edges
workflow.add_edge("transcriber", "summarizer")
workflow.add_edge("summarizer", "action_item_extractor")
workflow.add_edge("action_item_extractor", END)

# Set entry point
workflow.set_entry_point("transcriber")

# Compile
app_workflow = workflow.compile()
