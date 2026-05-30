import os
import time
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# --- ChromaDB client (persistent local storage) ---
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
COLLECTION_NAME = "video_chunks"


def get_collection():
    """Get or create the ChromaDB collection."""
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def clear_collection():
    """Delete and recreate collection (call before re-ingesting)."""
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return get_collection()


def get_embedder():
    """Return Gemini embedding model instance."""
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


def chunk_and_embed(ingest_result: dict) -> dict:
    """
    Take the output of ingest_video(), chunk the transcript,
    embed with Gemini, and store in ChromaDB.
    Each chunk tagged with video_label, metadata, engagement metrics.
    """
    transcript = ingest_result["transcript"]
    metadata = ingest_result["metadata"]
    video_label = ingest_result["video_label"]

    # --- Chunking (300 tokens ~ 1200 chars, 50 token overlap ~ 200 chars) ---
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(transcript)
    if not chunks:
        chunks = [transcript[:1200] if transcript else "[empty transcript]"]

    # --- Embed in small batches (Gemini free tier: 100 req/min) ---
    embedder = get_embedder()
    BATCH_SIZE = 10
    all_embeddings = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_embeddings = embedder.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        if i + BATCH_SIZE < len(chunks):
            time.sleep(1)  # stay under rate limit

    # --- Store in ChromaDB ---
    collection = get_collection()
    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{video_label}_{metadata.get('video_id_raw', 'unknown')}_{i}"
        chunk_metadata = {
            "video_label": video_label,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "platform": metadata.get("platform", ""),
            "title": metadata.get("title", ""),
            "creator": metadata.get("creator", ""),
            "url": metadata.get("url", ""),
            "views": metadata.get("views", 0),
            "likes": metadata.get("likes", 0),
            "comments": metadata.get("comments", 0),
            "engagement_rate": metadata.get("engagement_rate", 0.0),
            "follower_count": metadata.get("follower_count", 0),
            "upload_date": metadata.get("upload_date", ""),
            "duration": metadata.get("duration", 0),
            "hashtags": ", ".join(metadata.get("hashtags", [])),
        }
        documents.append(chunk)
        metadatas.append(chunk_metadata)
        ids.append(chunk_id)

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=all_embeddings,
        metadatas=metadatas,
    )

    print(f"[Embedder] Video {video_label}: {len(chunks)} chunks stored in ChromaDB")
    return {
        "video_label": video_label,
        "chunks_stored": len(chunks),
        "collection": COLLECTION_NAME,
    }


def query_collection(query: str, video_labels: list = None, n_results: int = 4) -> list:
    """
    Semantic search over stored chunks.
    Optionally filter by video_label ('A', 'B', or both).
    """
    embedder = get_embedder()
    query_embedding = embedder.embed_query(query)
    collection = get_collection()

    where_filter = None
    if video_labels and len(video_labels) == 1:
        where_filter = {"video_label": video_labels[0]}
    elif video_labels and len(video_labels) > 1:
        where_filter = {"video_label": {"$in": video_labels}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return output


def get_video_metadata(video_label: str) -> dict:
    """Retrieve metadata for a video from its first stored chunk."""
    collection = get_collection()
    results = collection.get(
        where={"video_label": video_label},
        limit=1,
        include=["metadatas"],
    )
    if results["metadatas"]:
        return results["metadatas"][0]
    return {}


# Quick test
if __name__ == "__main__":
    from ingest import ingest_video

    print("Testing embedder with Gemini...")
    result = ingest_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "A")
    embed_result = chunk_and_embed(result)
    print(f"Stored: {embed_result}")

    print("\nTesting semantic query...")
    hits = query_collection("love and commitment", video_labels=["A"], n_results=2)
    for hit in hits:
        print(f"  [Video {hit['metadata']['video_label']} chunk {hit['metadata']['chunk_index']}]")
        print(f"  Text: {hit['text'][:100]}...")
        print(f"  Distance: {hit['distance']:.4f}")
