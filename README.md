# Video RAG Chatbot

A full-stack RAG chatbot that compares two social media videos using AI. Input two YouTube/Instagram URLs and chat about them with streaming, cited responses.

## Stack

- **Frontend:** React + Vite
- **Backend:** FastAPI + SSE streaming
- **Orchestration:** LangChain
- **Embeddings:** Gemini text-embedding-001
- **Vector DB:** ChromaDB (local persistent)
- **LLM:** Groq llama-3.3-70b-versatile
- **Transcripts:** yt-dlp + youtube-transcript-api

## Setup

1. Clone the repo
2. Create .env in root with GEMINI_API_KEY and GROQ_API_KEY
3. Backend: cd backend, activate venv, pip install -r requirements.txt, uvicorn main:app --reload --port 8000
4. Frontend: cd frontend, npm install, npm run dev
5. Open http://localhost:5173

## Features

- Fetches transcripts and metadata (views, likes, comments, followers, hashtags)
- Computes engagement rate = (likes + comments) / views x 100
- Chunks and embeds transcripts into ChromaDB tagged by video
- Streaming chat with source citations like Video A chunk 0
- Conversation memory across turns
- Side-by-side video cards with full stats

## Cost at Scale (1000 creators/day)

- Gemini embeddings: free tier covers it
- Groq LLM: free tier 14400 req/day
- Hosting: ChromaDB local or Qdrant Cloud ~$25/mo
- Total: under $0.05 per creator session
