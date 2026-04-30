# AI Meeting Minutes Assistant - System Architecture Diagram

This diagram reflects the current implemented milestone version of the project.

## Mermaid Diagram

```mermaid
flowchart LR
    U[User] --> FE[Frontend Dashboard<br/>HTML / CSS / JavaScript]

    FE -->|Upload audio or .txt| API[FastAPI Backend<br/>main.py]
    FE -->|View history / delete record| API
    FE -->|Sync action items| API

    subgraph Speech["Speech Processing Layer"]
        WX[WhisperX<br/>ASR + Alignment + Word Timestamps]
        PA[pyannote.audio<br/>Speaker Diarization]
    end

    subgraph Workflow["LangGraph Multi-Agent Workflow"]
        CL[Cleaner Agent<br/>Normalize transcript]
        SU[Summary Agent<br/>Generate meeting minutes]
        AC[Action Agent<br/>Extract tasks / owners / deadlines]
        IN[Insight Agent<br/>Decisions / blockers / next focus]
        FU[Follow-up Agent<br/>Generate follow-up note]
    end

    subgraph LLM["LLM Layer"]
        GQ[Groq LLM<br/>llama models]
    end

    subgraph Storage["Persistence Layer"]
        DB[(SQLite<br/>meeting_history.db)]
    end

    subgraph Integration["External Integration"]
        FS[Feishu Tasks API]
        FO[Feishu open_id Resolver]
    end

    API -->|Audio file| WX
    WX -->|Timestamped transcript| PA
    PA -->|Speaker segments| WX
    WX -->|Speaker-aware transcript| CL

    API -->|Text transcript| CL

    CL --> SU
    CL --> AC
    CL --> IN

    SU <-->|LLM call| GQ
    AC <-->|LLM call| GQ
    IN <-->|LLM call| GQ
    CL <-->|LLM call| GQ
    FU <-->|LLM call| GQ

    SU --> FU
    AC --> FU
    IN --> FU

    FU --> API
    API --> DB
    DB --> API
    API --> FE

    API -->|Sync extracted action items| FS
    API -->|Resolve open_id from email/mobile| FO
```

## Short Explanation

- The **frontend dashboard** handles upload, template selection, result display, history browsing, and Feishu sync actions.
- The **FastAPI backend** coordinates the full pipeline and exposes REST APIs.
- For audio input, **WhisperX** performs transcription and alignment, while **pyannote** adds speaker diarization.
- The processed transcript enters a **LangGraph multi-agent workflow**:
  - `Cleaner Agent`
  - `Summary Agent`
  - `Action Agent`
  - `Insight Agent`
  - `Follow-up Agent`
- The reasoning agents call the **Groq LLM layer** for transcript cleaning, summarization, extraction, and follow-up generation.
- Final meeting results are stored in **SQLite** and returned to the frontend.
- Extracted action items can optionally be synchronized to **Feishu Tasks**.

## PPT-Friendly One-Line Summary

The system combines a frontend dashboard, a FastAPI backend, a WhisperX + pyannote speech pipeline, a LangGraph multi-agent reasoning workflow, SQLite persistence, and optional Feishu task integration.
