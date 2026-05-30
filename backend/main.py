import os
import json
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from ingest import ingest_video
from embedder import chunk_and_embed, clear_collection, get_video_metadata
from rag_chain import stream_rag_response

load_dotenv()

app = FastAPI(title="Video RAG Chatbot API", version="1.0.0")

# --- CORS (allow React frontend on port 5173) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory session store ---
# Key: session_id, Value: list of {role, content} dicts
sessions: dict = {}

# --- In-memory video store ---
# Tracks which videos have been ingested this session
ingested_videos: dict = {}  # {"A": {...metadata}, "B": {...metadata}}


# ── Request / Response Models ─────────────────────────────────────────────────

class IngestRequest(BaseModel):
    url_a: str
    url_b: str
    session_id: str = "default"

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"

class VideoMeta(BaseModel):
    video_label: str
    title: str
    creator: str
    platform: str
    views: int
    likes: int
    comments: int
    engagement_rate: float
    follower_count: int
    upload_date: str
    duration: int
    hashtags: str
    url: str

class IngestResponse(BaseModel):
    success: bool
    video_a: Optional[dict] = None
    video_b: Optional[dict] = None
    message: str = ""

class StatusResponse(BaseModel):
    ingested: bool
    videos: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "Video RAG Chatbot API running"}


@app.get("/status")
def status():
    """Check if videos have been ingested."""
    return StatusResponse(
        ingested=len(ingested_videos) == 2,
        videos=ingested_videos,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_videos(req: IngestRequest):
    """
    Ingest two video URLs, fetch transcripts + metadata,
    chunk + embed into ChromaDB. Clears previous data first.
    """
    try:
        # Clear existing ChromaDB data for fresh ingestion
        clear_collection()
        ingested_videos.clear()

        # Clear session history too
        if req.session_id in sessions:
            sessions[req.session_id] = []

        # --- Ingest Video A ---
        print(f"[Ingest] Fetching Video A: {req.url_a}")
        result_a = ingest_video(req.url_a, "A")
        embed_a = chunk_and_embed(result_a)
        ingested_videos["A"] = result_a["metadata"]

        # --- Ingest Video B ---
        print(f"[Ingest] Fetching Video B: {req.url_b}")
        result_b = ingest_video(req.url_b, "B")
        embed_b = chunk_and_embed(result_b)
        ingested_videos["B"] = result_b["metadata"]

        return IngestResponse(
            success=True,
            video_a=result_a["metadata"],
            video_b=result_b["metadata"],
            message=f"Ingested {embed_a['chunks_stored']} chunks for A, {embed_b['chunks_stored']} chunks for B",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    SSE streaming chat endpoint.
    Retrieves relevant chunks, streams LLM response token by token.
    Maintains conversation memory per session.
    """
    if len(ingested_videos) < 2:
        raise HTTPException(
            status_code=400,
            detail="Please ingest two videos first via POST /ingest"
        )

    # Get or create session history
    history = sessions.get(req.session_id, [])

    async def event_stream():
        full_response = ""
        try:
            # Run sync generator in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def run_rag():
                tokens = []
                for token in stream_rag_response(req.question, history):
                    tokens.append(token)
                return tokens

            tokens = await loop.run_in_executor(None, run_rag)

            for token in tokens:
                full_response += token
                # SSE format: data: \n\n
                payload = json.dumps({"token": token, "done": False})
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)  # yield control

            # Signal completion
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
            return

        # Save to session history after streaming completes
        sessions[req.session_id] = history + [
            {"role": "user", "content": req.question},
            {"role": "assistant", "content": full_response},
        ]
        # Keep last 10 turns only
        sessions[req.session_id] = sessions[req.session_id][-10:]

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Clear conversation history for a session."""
    sessions.pop(session_id, None)
    return {"cleared": True, "session_id": session_id}


@app.get("/metadata/{video_label}")
def get_metadata(video_label: str):
    """Get stored metadata for a specific video (A or B)."""
    meta = get_video_metadata(video_label.upper())
    if not meta:
        raise HTTPException(status_code=404, detail=f"Video {video_label} not found")
    return meta
