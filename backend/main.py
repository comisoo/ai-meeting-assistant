import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from groq import Groq

# Load environment variables
load_dotenv()

# Check GROQ API KEY
if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") == "your_groq_api_key_here":
    print("WARNING: GROQ_API_KEY is missing or invalid in .env")

# Import LangGraph workflow
from app.agents.workflow import app_workflow

app = FastAPI(
    title="AI Meeting Minutes Assistant",
    description="Backend API for processing meeting transcripts using Groq & LangGraph",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Minutes Assistant API (Powered by Groq)"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "groq_key_configured": bool(os.environ.get("GROQ_API_KEY") and os.environ.get("GROQ_API_KEY") != "your_groq_api_key_here")}

@app.post("/api/process-audio")
async def process_audio(
    file: UploadFile = File(...),
    template: str = Form("general")
):
    # 1. Determine file type
    is_audio = file.filename.endswith(('.mp3', '.m4a', '.wav', '.webm', '.mp4', '.ogg'))
    is_text = file.filename.endswith('.txt')
    
    if not (is_audio or is_text):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload an audio file or a .txt transcript.")

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    transcript = ""

    # 2. Process File
    try:
        if is_audio:
            # We must save the audio file temporarily for the Groq client
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
                shutil.copyfileobj(file.file, tmp_file)
                tmp_path = tmp_file.name
            
            try:
                with open(tmp_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        file=(file.filename, audio_file.read()),
                        model="whisper-large-v3",
                        response_format="json"
                    )
                    transcript = transcription.text
            finally:
                os.unlink(tmp_path) # cleanup
        else: # is_text
            content = await file.read()
            try:
                transcript = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    transcript = content.decode('gbk')
                except UnicodeDecodeError:
                    transcript = content.decode('latin1', errors='ignore')
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading or transcribing file: {str(e)}")

    if not transcript:
        raise HTTPException(status_code=500, detail="Transcription failed or file was empty.")

    # 3. Trigger LangGraph Workflow
    try:
        initial_state = {
            "transcript": transcript,
            "template": template
        }
        
        # Invoke workflow
        result = app_workflow.invoke(initial_state)
        
        return {
            "filename": file.filename,
            "template": template,
            "cleaned_transcript": result.get("cleaned_transcript"),
            "summary": result.get("summary"),
            "action_items": result.get("action_items", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
