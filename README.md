# AI Meeting Minutes Assistant

An AI-based meeting intelligence tool featuring a lightweight multi-agent workflow, persistent meeting history, and a WhisperX-based transcription pipeline with speaker diarization for audio uploads.

## Architecture

- **Backend**: Python 3.10+, FastAPI, LangGraph, SQLite
- **Speech Stack**:
  - `WhisperX`: ASR, alignment, and word-level timestamps
  - `pyannote`: speaker diarization through WhisperX integration
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

# Optional: Feishu task sync
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
# FEISHU_BASE_URL=https://open.feishu.cn
# FEISHU_TASK_ORIGIN_NAME=AI Meeting Minutes Assistant
# FEISHU_TASK_ORIGIN_URL=http://localhost:8080
# FEISHU_DEFAULT_OPEN_ID=your_open_id_here
# FEISHU_DEFAULT_COLLABORATOR_IDS=open_id_1,open_id_2
# FEISHU_DEFAULT_FOLLOWER_IDS=open_id_1,open_id_2

# WhisperX transcription and diarization
WHISPERX_MODEL=small
# WHISPERX_MODEL_DIR=C:\models\faster-whisper-small
WHISPERX_DEVICE=auto
WHISPERX_COMPUTE_TYPE=int8
WHISPERX_BATCH_SIZE=4
WHISPERX_THREADS=8
# WHISPERX_LANGUAGE=en
WHISPERX_VAD_METHOD=silero
# WHISPERX_DOWNLOAD_ROOT=C:\models\whisperx-cache
# WHISPERX_LOCAL_FILES_ONLY=0
# WHISPERX_ALIGN_MODEL_DIR=C:\models\whisperx-cache
# WHISPERX_ALIGN_LOCAL_FILES_ONLY=0

# Speaker diarization options for WhisperX
DIARIZATION_ENABLED=1

# WhisperX diarization currently uses the local pyannote community model
HUGGINGFACE_TOKEN=your_huggingface_token

# Optional
DIARIZATION_BACKEND=community-1
# DIARIZATION_DEVICE=auto
# DIARIZATION_NUM_SPEAKERS=2
# DIARIZATION_MIN_SPEAKERS=2
# DIARIZATION_MAX_SPEAKERS=6
```

Notes:
- WhisperX handles transcription, alignment, and speaker-to-word assignment.
- Feishu sync is implemented as a lightweight post-processing integration. The minimal version creates one Feishu task per extracted action item and does not yet map assignees to real Feishu user IDs.
- Without user OAuth, the backend does not know the true current Feishu user automatically. The practical minimal workaround is to configure `FEISHU_DEFAULT_OPEN_ID`, which will add that user as both collaborator and follower on created tasks.
- `community-1` uses local `pyannote.audio` inference through WhisperX and requires a Hugging Face token with access to the model.
- The backend now loads `backend/.env` by file path, so diarization config still works even if you start the server from the repo root.
- A working PyTorch stack is required. WhisperX prefers `ffmpeg` for audio decoding, and this backend falls back to `soundfile` when `ffmpeg` is unavailable.
- If Hugging Face downloads are unstable, you can point `WHISPERX_DOWNLOAD_ROOT` at a local cache directory and later set `WHISPERX_LOCAL_FILES_ONLY=1` after the models have been downloaded once.
- On CPU, the fastest practical setup is usually `WHISPERX_MODEL=small`, `WHISPERX_COMPUTE_TYPE=int8`, `WHISPERX_VAD_METHOD=silero`, and setting `WHISPERX_LANGUAGE` when you already know the meeting language.

## API Highlights

- `POST /api/process-audio`: process an uploaded audio file or `.txt` transcript
- `GET /api/meetings`: list recent saved meetings
- `GET /api/meetings/{id}`: load one saved meeting in full
- `POST /api/meetings/{id}/sync-feishu`: sync extracted action items to Feishu Tasks
- `POST /api/feishu/resolve-open-id`: resolve a user's Feishu `open_id` from email or mobile
- `GET /health`: backend health, storage mode, and diarization mode

Example request for resolving a Feishu `open_id`:

```bash
curl -X POST http://127.0.0.1:8000/api/feishu/resolve-open-id \
  -H "Content-Type: application/json" \
  -d "{\"emails\": [\"your_email@example.com\"]}"
```

## Notes

- Processed meetings are stored in `backend/meeting_history.db`.
- Audio uploads are transcribed with WhisperX, aligned to word timestamps, diarized with pyannote, and then passed into the LangGraph workflow as a speaker-aware transcript.
- The backend now tries `GROQ_PRIMARY_MODEL` first and will fall back to `GROQ_FALLBACK_MODELS` if it hits a Groq rate limit.
