# AI Meeting Minutes Assistant

An AI-based meeting intelligence tool featuring a lightweight multi-agent workflow, persistent meeting history, and true speaker diarization for audio uploads.

## Architecture

- **Backend**: Python 3.10+, FastAPI, LangGraph, SQLite
- **Speech Stack**:
  - `Groq Whisper`: audio transcription with timestamps
  - `pyannote`: speaker diarization for true speaker segmentation
- **Agents Workflow**:
  - `Cleaner Agent`: normalizes raw bilingual transcripts
  - `Summarizer Agent`: generates structured meeting minutes
  - `Action Item Agent`: extracts tasks, owners, and deadlines
  - `Insight Agent`: captures tone, decisions, blockers, and next focus
  - `Follow-up Agent`: drafts the post-meeting follow-up plan
- **Frontend**: Vanilla HTML/CSS/JS

## Features

- Multi-agent fan-out/fan-in meeting processing flow
- Audio or `.txt` transcript upload
- True speaker diarization for audio files
- Structured summaries and action-item extraction
- Meeting insights and follow-up plan generation
- SQLite-backed meeting history with reloadable past sessions

## Setup

### 1. Backend

```bash
cd backend

# Option A: Conda
conda create -n ai-meeting python=3.10 -y
conda activate ai-meeting

# Option B: venv
# python -m venv venv
# .\venv\Scripts\activate

pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 2. Frontend

```bash
cd frontend
python -m http.server 8080
```

Then visit `http://localhost:8080` in your browser.

## Environment Variables

Add these to `backend/.env`:

```env
GROQ_API_KEY=your_groq_key
GROQ_PRIMARY_MODEL=llama-3.1-8b-instant
GROQ_FALLBACK_MODELS=llama-3.3-70b-versatile

# Speaker diarization options
DIARIZATION_ENABLED=1

# Optional offline local model directory
# DIARIZATION_LOCAL_PATH=C:\models\speaker-diarization-community-1

# Choose one of the following token paths:
HUGGINGFACE_TOKEN=your_huggingface_token
# or
PYANNOTEAI_API_KEY=your_pyannoteai_key

# Optional
DIARIZATION_BACKEND=community-1
# DIARIZATION_BACKEND=precision-2
# DIARIZATION_DEVICE=auto
# DIARIZATION_NUM_SPEAKERS=2
# DIARIZATION_MIN_SPEAKERS=2
# DIARIZATION_MAX_SPEAKERS=6
```

Notes:
- If `DIARIZATION_LOCAL_PATH` is set, the backend loads the diarization model from that local directory first and does not need to download from Hugging Face at runtime.
- `community-1` uses local `pyannote.audio` inference and requires a Hugging Face token with access to the model.
- `precision-2` uses the pyannote hosted backend and requires a pyannoteAI API key.
- For local diarization, `ffmpeg` and the PyTorch stack must be available in your environment.

## Offline Local Model

If Hugging Face connectivity is unreliable, you can download the diarization model once and point the backend to a local folder.

Example:

```env
DIARIZATION_ENABLED=1
DIARIZATION_LOCAL_PATH=C:\models\speaker-diarization-community-1
DIARIZATION_DEVICE=auto
```

Then keep `DIARIZATION_BACKEND=community-1` or omit it entirely. The backend will prefer the local directory whenever `DIARIZATION_LOCAL_PATH` is set.

## API Highlights

- `POST /api/process-audio`: process an uploaded audio file or `.txt` transcript
- `GET /api/meetings`: list recent saved meetings
- `GET /api/meetings/{id}`: load one saved meeting in full
- `GET /health`: backend health, storage mode, and diarization mode

## Notes

- Processed meetings are stored in `backend/meeting_history.db`.
- Audio uploads are transcribed with timestamps, diarized with pyannote, aligned to speakers, and then passed into the LangGraph workflow as a speaker-aware transcript.
- The backend now tries `GROQ_PRIMARY_MODEL` first and will fall back to `GROQ_FALLBACK_MODELS` if it hits a Groq rate limit.
