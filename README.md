# AI Meeting Minutes Assistant

An AI-based automatic meeting minutes generator featuring a Multi-Agent System. Optimized for code-switching environments (e.g., mixing English and Chinese) and custom template extraction.

## Architecture

- **Backend**: Python 3.10+, FastAPI, LangGraph
- **Agents Workflow**: 
  - `Transcription Agent`: Whisper integration -> code-switching cleaning
  - `Summarizer Agent`: LangChain LLM -> template-based summary
  - `ActionItem Agent`: Extractor -> task list
- **Frontend**: Vanilla HTML/CSS/JS (Beautiful Modern UI)

## Setup Instructions

### 1. Backend

Open a terminal and navigate to the `backend` directory.

```bash
cd backend
<<<<<<< HEAD

# Option A: Using Conda (Recommended)
conda create -n ai-meeting python=3.10 -y
conda activate ai-meeting

# Option B: Using venv
# python -m venv venv
# .\venv\Scripts\activate

# Install dependencies (applicable for both Conda and venv)
pip install -r requirements.txt


=======
# Create virtual environment (optional but recommended)
python -m venv venv
# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

>>>>>>> 6a9b581612307d82b4c1a68e19cc9ebcf61d1f9d
# Run the FastAPI development server
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### 2. Frontend

Open a new terminal or file explorer and navigate to the `frontend` directory.
Simply open `index.html` in any modern web browser or use a quick local server:
```bash
cd frontend
python -m http.server 8080
```
Then visit `http://localhost:8080` in your browser.

## Features

- **Agent Framework**: Powered by LangGraph for structured workflows.
- **Glassmorphism UI**: Beautiful, dynamic interface.
- **Micro-Animations**: Setup with step-by-step processing loaders.
- **Custom Templates**: Pre-configured select options for Agile, general, and brainstorming meetings.
