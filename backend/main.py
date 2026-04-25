import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.agents.workflow import app_workflow
from app.diarization import get_diarization_config, is_diarization_enabled
from app.env import load_app_env
from app.storage import delete_meeting, get_meeting, init_db, list_meetings, save_meeting
from app.transcription import (
    get_whisperx_batch_size,
    get_whisperx_device,
    get_whisperx_language,
    get_whisperx_model_name,
    get_whisperx_threads,
    get_whisperx_vad_method,
    process_audio_with_whisperx,
)

load_app_env()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".webm", ".mp4", ".ogg"}
SUPPORTED_TEXT_SUFFIXES = {".txt"}

if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
    print("WARNING: GROQ_API_KEY is missing or invalid in .env")


app = FastAPI(
    title="AI Meeting Minutes Assistant",
    description="Backend API for processing meeting transcripts using WhisperX, Groq, pyannote, and LangGraph",
    version="1.4.0",
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


def is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "rate limit" in message or "rate_limit_exceeded" in message or "error code: 429" in message


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
    transcription_device = get_whisperx_device()
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
        "transcription_engine": "whisperx",
        "transcription_model": get_whisperx_model_name(transcription_device),
        "transcription_device": transcription_device,
        "transcription_language": get_whisperx_language() or "auto",
        "transcription_vad_method": get_whisperx_vad_method(transcription_device),
        "transcription_batch_size": get_whisperx_batch_size(transcription_device),
        "transcription_threads": get_whisperx_threads(),
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


@app.delete("/api/meetings/{meeting_id}")
def delete_meeting_detail(meeting_id: int):
    deleted = delete_meeting(meeting_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {"deleted": True, "meeting_id": meeting_id}


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
            prepared_input = process_audio_with_whisperx(temp_path)
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
