import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

from app.agents.workflow import app_workflow
from app.diarization import diarize_audio, get_diarization_config, is_diarization_enabled
from app.storage import get_meeting, init_db, list_meetings, save_meeting

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".webm", ".mp4", ".ogg"}
SUPPORTED_TEXT_SUFFIXES = {".txt"}

if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
    print("WARNING: GROQ_API_KEY is missing or invalid in .env")


app = FastAPI(
    title="AI Meeting Minutes Assistant",
    description="Backend API for processing meeting transcripts using Groq, pyannote, and LangGraph",
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()


def get_file_suffix(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def get_value(item: Any, field: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "rate limit" in message or "rate_limit_exceeded" in message or "error code: 429" in message


def normalize_transcript_entries(entries: Any, text_field: str) -> List[Dict[str, Any]]:
    normalized = []
    for entry in entries or []:
        text = get_value(entry, text_field, "") or get_value(entry, "text", "")
        start = get_value(entry, "start", None)
        end = get_value(entry, "end", None)
        if start is None or end is None or text is None:
            continue
        normalized.append(
            {
                "text": str(text).strip(),
                "start": float(start),
                "end": float(end),
            }
        )
    return [entry for entry in normalized if entry["text"]]


def save_upload_to_temp(file: UploadFile) -> str:
    suffix = get_file_suffix(file.filename) or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        return tmp_file.name


async def read_text_upload(file: UploadFile) -> str:
    content = await file.read()
    for encoding in ("utf-8", "gbk", "latin1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("latin1", errors="ignore")


def transcribe_audio(audio_path: str, filename: str) -> Dict[str, Any]:
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    client = Groq(api_key=GROQ_API_KEY)

    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )

    words = normalize_transcript_entries(get_value(transcription, "words", []), "word")
    segments = normalize_transcript_entries(get_value(transcription, "segments", []), "text")

    return {
        "text": get_value(transcription, "text", "") or "",
        "words": words,
        "segments": segments,
    }


def compute_overlap(unit: Dict[str, Any], diarization_segment: Dict[str, Any]) -> float:
    return max(
        0.0,
        min(float(unit["end"]), float(diarization_segment["end"]))
        - max(float(unit["start"]), float(diarization_segment["start"])),
    )


def assign_speakers_to_units(
    units: List[Dict[str, Any]], diarization_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if not units or not diarization_segments:
        return []

    assigned_units = []
    last_speaker = "Unknown"

    for unit in units:
        best_segment: Optional[Dict[str, Any]] = None
        best_overlap = 0.0

        for diarization_segment in diarization_segments:
            overlap = compute_overlap(unit, diarization_segment)
            if overlap > best_overlap:
                best_overlap = overlap
                best_segment = diarization_segment

        speaker = (
            best_segment["speaker"]
            if best_segment is not None and best_overlap > 0
            else last_speaker
        )
        if speaker == "Unknown" and best_segment is not None:
            speaker = best_segment["speaker"]

        last_speaker = speaker
        assigned_units.append({**unit, "speaker": speaker})

    return assigned_units


def merge_speaker_units(units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not units:
        return []

    merged = []
    current = dict(units[0])

    for unit in units[1:]:
        same_speaker = unit["speaker"] == current["speaker"]
        short_gap = float(unit["start"]) - float(current["end"]) <= 1.2

        if same_speaker and short_gap:
            current["text"] = f"{current['text']} {unit['text']}".strip()
            current["end"] = unit["end"]
        else:
            merged.append(current)
            current = dict(unit)

    merged.append(current)
    return merged


def format_speaker_label(raw_speaker: str, speaker_map: Dict[str, str]) -> str:
    if raw_speaker not in speaker_map:
        speaker_map[raw_speaker] = f"Speaker {len(speaker_map) + 1}"
    return speaker_map[raw_speaker]


def build_speaker_aware_transcript(speaker_segments: List[Dict[str, Any]]) -> str:
    if not speaker_segments:
        return ""

    speaker_map: Dict[str, str] = {}
    lines = []
    for segment in speaker_segments:
        speaker_label = format_speaker_label(segment["speaker"], speaker_map)
        lines.append(f"{speaker_label}: {segment['text']}")
    return "\n\n".join(lines)


def enrich_speaker_segments(speaker_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    speaker_map: Dict[str, str] = {}
    enriched_segments = []
    for segment in speaker_segments:
        enriched_segments.append(
            {
                **segment,
                "speaker_label": format_speaker_label(segment["speaker"], speaker_map),
            }
        )
    return enriched_segments


def process_audio_with_diarization(audio_path: str, filename: str) -> Dict[str, Any]:
    transcription = transcribe_audio(audio_path, filename)
    diarization_error = ""

    try:
        diarization_result = diarize_audio(audio_path)
    except Exception as exc:
        fallback_config = get_diarization_config()
        diarization_result = {
            "status": "error",
            "backend": fallback_config["backend"],
            "segments": [],
            "exclusive_segments": [],
        }
        diarization_error = str(exc)

    diarization_segments = (
        diarization_result["exclusive_segments"] or diarization_result["segments"]
    )

    transcript_units = transcription["words"] or transcription["segments"]
    assigned_units = assign_speakers_to_units(transcript_units, diarization_segments)
    speaker_segments = enrich_speaker_segments(merge_speaker_units(assigned_units))
    speaker_aware_transcript = build_speaker_aware_transcript(speaker_segments)

    return {
        "transcript": transcription["text"],
        "speaker_aware_transcript": speaker_aware_transcript,
        "speaker_segments": speaker_segments,
        "diarization_segments": diarization_result["segments"],
        "diarization_status": diarization_result["status"],
        "diarization_backend": diarization_result.get("backend", "none"),
        "diarization_error": diarization_error,
    }


def build_text_payload(transcript: str) -> Dict[str, Any]:
    return {
        "transcript": transcript,
        "speaker_aware_transcript": "",
        "speaker_segments": [],
        "diarization_segments": [],
        "diarization_status": "not_available",
        "diarization_backend": "text_input",
        "diarization_error": "",
    }


def build_meeting_payload(
    filename: str,
    template: str,
    prepared_input: Dict[str, Any],
    workflow_result: dict,
) -> dict:
    return {
        "filename": filename,
        "template": template,
        "transcript": prepared_input["transcript"],
        "cleaned_transcript": workflow_result.get("cleaned_transcript", ""),
        "speaker_aware_transcript": prepared_input.get("speaker_aware_transcript", ""),
        "summary": workflow_result.get("summary", ""),
        "action_items": workflow_result.get("action_items", []),
        "insights": workflow_result.get("insights", {}),
        "follow_up": workflow_result.get("follow_up", ""),
        "speaker_segments": prepared_input.get("speaker_segments", []),
        "diarization_segments": prepared_input.get("diarization_segments", []),
        "diarization_status": prepared_input.get("diarization_status", "not_available"),
        "diarization_backend": prepared_input.get("diarization_backend", "none"),
        "diarization_error": prepared_input.get("diarization_error", ""),
    }


@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Minutes Assistant API (Powered by Groq)"}


@app.get("/health")
def health_check():
    diarization_config = get_diarization_config()
    return {
        "status": "healthy",
        "groq_key_configured": bool(
            GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here"
        ),
        "workflow_mode": "multi_agent_fanout",
        "history_storage": "sqlite",
        "diarization_enabled": is_diarization_enabled(),
        "diarization_backend": diarization_config["backend"],
        "diarization_model": diarization_config["model"],
    }


@app.get("/api/meetings")
def get_meetings(limit: int = 10):
    return {"meetings": list_meetings(limit=limit)}


@app.get("/api/meetings/{meeting_id}")
def get_meeting_detail(meeting_id: int):
    meeting = get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return meeting


@app.post("/api/process-audio")
async def process_audio(
    file: UploadFile = File(...),
    template: str = Form("general"),
):
    suffix = get_file_suffix(file.filename)
    is_audio = suffix in SUPPORTED_AUDIO_SUFFIXES
    is_text = suffix in SUPPORTED_TEXT_SUFFIXES

    if not (is_audio or is_text):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload an audio file or a .txt transcript.",
        )

    temp_path = None
    try:
        if is_audio:
            temp_path = save_upload_to_temp(file)
            prepared_input = process_audio_with_diarization(temp_path, file.filename)
        else:
            transcript = await read_text_upload(file)
            prepared_input = build_text_payload(transcript)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading, transcribing, or diarizing file: {exc}",
        ) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    workflow_input = (
        prepared_input["speaker_aware_transcript"] or prepared_input["transcript"]
    ).strip()

    if not workflow_input:
        raise HTTPException(
            status_code=500,
            detail="Transcription failed or the uploaded file was empty.",
        )

    try:
        workflow_result = app_workflow.invoke(
            {"transcript": workflow_input, "template": template}
        )
    except Exception as exc:
        if is_rate_limit_error(exc):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Groq rate limit reached while generating meeting outputs. "
                    f"Details: {exc}"
                ),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed: {exc}",
        ) from exc

    payload = build_meeting_payload(file.filename, template, prepared_input, workflow_result)
    return save_meeting(payload)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
