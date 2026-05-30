import { useState } from "react";
import axios from "axios";
import VideoCard from "./VideoCard";
import ChatPanel from "./ChatPanel";

const API = "http://localhost:8000";
const SESSION_ID = "session_" + Math.random().toString(36).slice(2);

export default function App() {
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");
  const [loading, setLoading] = useState(false);
  const [ingested, setIngested] = useState(false);
  const [videoA, setVideoA] = useState(null);
  const [videoB, setVideoB] = useState(null);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);

  const handleIngest = async () => {
    if (!urlA.trim() || !urlB.trim()) { setError("Please enter both video URLs."); return; }
    setError(""); setLoading(true); setIngested(false);
    setVideoA(null); setVideoB(null); setMessages([]);
    try {
      const res = await axios.post(`${API}/ingest`, { url_a: urlA.trim(), url_b: urlB.trim(), session_id: SESSION_ID });
      setVideoA(res.data.video_a); setVideoB(res.data.video_b); setIngested(true);
    } catch (e) {
      setError(e.response?.data?.detail || "Ingestion failed.");
    } finally { setLoading(false); }
  };

  const handleChat = async (question) => {
    if (!question.trim() || streaming) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setStreaming(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: SESSION_ID }),
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { ...updated[updated.length - 1], content: updated[updated.length - 1].content + data.token };
                return updated;
              });
            }
          } catch (_) {}
        }
      }
    } catch (e) {
      setMessages((prev) => { const u = [...prev]; u[u.length-1].content = "Connection error."; return u; });
    } finally { setStreaming(false); }
  };

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <h1 style={styles.title}>Video RAG Analyser</h1>
        <p style={styles.subtitle}>Compare two videos with AI-powered insights</p>
      </header>
      <div style={styles.inputSection}>
        <div style={styles.inputRow}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Video A (YouTube)</label>
            <input style={styles.input} placeholder="https://youtube.com/watch?v=..." value={urlA} onChange={(e) => setUrlA(e.target.value)} disabled={loading} />
          </div>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Video B (YouTube or Instagram)</label>
            <input style={styles.input} placeholder="https://instagram.com/reel/..." value={urlB} onChange={(e) => setUrlB(e.target.value)} disabled={loading} />
          </div>
          <button style={{ ...styles.button, opacity: loading ? 0.6 : 1 }} onClick={handleIngest} disabled={loading}>
            {loading ? "Analysing..." : "Analyse Videos"}
          </button>
        </div>
        {error && <p style={styles.error}>{error}</p>}
        {loading && <p style={styles.loadingMsg}>Fetching transcripts, computing embeddings, storing in ChromaDB...</p>}
      </div>
      {ingested && (
        <div style={styles.cardsRow}>
          <VideoCard video={videoA} label="A" />
          <VideoCard video={videoB} label="B" />
        </div>
      )}
      {ingested && (
        <ChatPanel
          messages={messages}
          onSend={handleChat}
          streaming={streaming}
          suggestions={[
            "Why did Video A get more engagement than Video B?",
            "What is the engagement rate of each video?",
            "Compare the hooks in the first 5 seconds.",
            "Who is the creator of Video B and what is their follower count?",
            "Suggest improvements for B based on what worked in A.",
          ]}
        />
      )}
    </div>
  );
}

const styles = {
  root: { minHeight: "100vh", background: "#0f0f0f", color: "#e8e8e8", fontFamily: "'Inter', system-ui, sans-serif", padding: "0 0 60px 0" },
  header: { padding: "32px 40px 20px", borderBottom: "1px solid #1e1e1e" },
  title: { fontSize: 28, fontWeight: 700, margin: 0, color: "#ffffff" },
  subtitle: { fontSize: 14, color: "#888", margin: "6px 0 0" },
  inputSection: { padding: "24px 40px", borderBottom: "1px solid #1e1e1e" },
  inputRow: { display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" },
  inputGroup: { flex: 1, minWidth: 240, display: "flex", flexDirection: "column", gap: 6 },
  label: { fontSize: 12, fontWeight: 500, color: "#aaa", textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#1a1a1a", border: "1px solid #2e2e2e", borderRadius: 8, padding: "10px 14px", fontSize: 14, color: "#e8e8e8", outline: "none", width: "100%", boxSizing: "border-box" },
  button: { background: "#7c3aed", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap", height: 42, alignSelf: "flex-end" },
  error: { color: "#f87171", fontSize: 13, marginTop: 10 },
  loadingMsg: { color: "#888", fontSize: 13, marginTop: 10 },
  cardsRow: { display: "flex", gap: 20, padding: "24px 40px", flexWrap: "wrap" },
};
