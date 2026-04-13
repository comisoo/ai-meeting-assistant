from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="AI Meeting Minutes Assistant",
    description="Backend API for processing meeting transcripts using LangGraph",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Minutes Assistant API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/process-audio")
async def process_audio(file: UploadFile = File(...)):
    # Placeholder for Whisper transcription + LangGraph agent workflow
    return {
        "filename": file.filename,
        "message": "Audio uploaded successfully. Processing will be handled by agents."
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
