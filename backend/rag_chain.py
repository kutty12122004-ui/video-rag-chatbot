import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from embedder import query_collection, get_video_metadata

load_dotenv()

# --- LLM ---
def get_llm():
    from langchain_groq import ChatGroq
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.7,
        streaming=True,
    )

SYSTEM_PROMPT = """You are a social media analytics assistant helping creators understand their video performance.

You have access to transcripts and metadata for two videos: Video A and Video B.
When answering:
1. Always cite your sources like: [Video A, chunk 2] or [Video B, chunk 0]
2. Use actual engagement metrics (views, likes, comments, engagement rate) from the context
3. Be specific and actionable — creators want real insights, not generic advice
4. If comparing videos, structure your answer clearly with A vs B sections
5. Keep answers concise but data-driven

Context will be provided with each question."""


def format_chunks_as_context(chunks: list) -> str:
    """Format retrieved chunks into a readable context block."""
    if not chunks:
        return "No relevant transcript chunks found."

    context_parts = []
    for chunk in chunks:
        meta = chunk["metadata"]
        label = meta.get("video_label", "?")
        idx = meta.get("chunk_index", 0)
        creator = meta.get("creator", "Unknown")
        title = meta.get("title", "Unknown")
        views = meta.get("views", 0)
        likes = meta.get("likes", 0)
        comments = meta.get("comments", 0)
        eng = meta.get("engagement_rate", 0)

        context_parts.append(
            f"[Video {label}, chunk {idx}]\n"
            f"Title: {title}\n"
            f"Creator: {creator}\n"
            f"Views: {views:,} | Likes: {likes:,} | Comments: {comments:,} | Engagement: {eng}%\n"
            f"Transcript excerpt:\n{chunk['text']}\n"
        )

    return "\n---\n".join(context_parts)


def format_metadata_summary(video_labels: list) -> str:
    """Get metadata summary for specified videos."""
    parts = []
    for label in video_labels:
        meta = get_video_metadata(label)
        if meta:
            parts.append(
                f"Video {label}: '{meta.get('title', 'Unknown')}' by {meta.get('creator', 'Unknown')} "
                f"| {meta.get('platform', '').title()} | {meta.get('views', 0):,} views "
                f"| {meta.get('engagement_rate', 0)}% engagement rate "
                f"| {meta.get('follower_count', 0):,} followers"
            )
    return "\n".join(parts) if parts else "No metadata available."


def build_messages(history: list, question: str, context: str, meta_summary: str):
    """Build the full message list for the LLM."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Add conversation history (last 6 turns = 3 exchanges)
    for turn in history[-6:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))

    # Add current question with context
    user_content = f"""Video Overview:
{meta_summary}

Relevant transcript context:
{context}

Question: {question}"""

    messages.append(HumanMessage(content=user_content))
    return messages


def stream_rag_response(question: str, history: list):
    """
    Main RAG function. Retrieves chunks, builds context, streams LLM response.
    Yields text chunks as they stream.

    Args:
        question: The user's question
        history: List of {role, content} dicts (conversation memory)

    Yields:
        str: streamed text tokens
    """
    # --- Retrieve relevant chunks from both videos ---
    chunks = query_collection(
        query=question,
        video_labels=["A", "B"],
        n_results=4,
    )

    # --- Build context ---
    context = format_chunks_as_context(chunks)
    meta_summary = format_metadata_summary(["A", "B"])

    # --- Build messages ---
    messages = build_messages(history, question, context, meta_summary)

    # --- Stream LLM response ---
    llm = get_llm()
    full_response = ""
    for chunk in llm.stream(messages):
        token = chunk.content
        if token:
            full_response += token
            yield token

    # Return full response for history (via generator send — not used here,
    # caller appends to history after collecting streamed tokens)


def get_rag_response(question: str, history: list) -> str:
    """Non-streaming version — collects full response. Used for testing."""
    return "".join(stream_rag_response(question, history))


# Quick test
if __name__ == "__main__":
    print("Testing RAG chain...")
    history = []

    q1 = "What is the engagement rate of Video A and who is the creator?"
    print(f"\nQ: {q1}")
    print("A: ", end="", flush=True)
    answer = get_rag_response(q1, history)
    print(answer)

    history.append({"role": "user", "content": q1})
    history.append({"role": "assistant", "content": answer})

    q2 = "What themes does the transcript cover?"
    print(f"\nQ: {q2}")
    print("A: ", end="", flush=True)
    answer2 = get_rag_response(q2, history)
    print(answer2)
