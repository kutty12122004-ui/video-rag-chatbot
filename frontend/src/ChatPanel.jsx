import { useState, useEffect, useRef } from "react";

export default function ChatPanel({ messages, onSend, streaming, suggestions }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || streaming) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.panelHeader}>
        <span style={styles.panelTitle}>Ask about your videos</span>
        {streaming && <span style={styles.streamingBadge}>Streaming...</span>}
      </div>
      {messages.length === 0 && (
        <div style={styles.suggestions}>
          {suggestions.map((s) => (
            <button key={s} style={styles.chip} onClick={() => onSend(s)} disabled={streaming}>
              {s}
            </button>
          ))}
        </div>
      )}
      <div style={styles.messages}>
        {messages.map((msg, i) => (
          <div key={i} style={{ ...styles.msgRow, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{ ...styles.bubble, ...(msg.role === "user" ? styles.userBubble : styles.aiBubble) }}>
              {msg.role === "assistant" ? <FormattedMessage text={msg.content} /> : msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div style={styles.inputRow}>
        <textarea
          style={styles.textarea}
          placeholder="Ask anything about Video A or B..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={2}
          disabled={streaming}
        />
        <button
          style={{ ...styles.sendBtn, opacity: streaming || !input.trim() ? 0.5 : 1 }}
          onClick={handleSend}
          disabled={streaming || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

function FormattedMessage({ text }) {
  if (!text) return <span style={{ color: "#555" }}>thinking...</span>;
  const parts = text.split(/(\[Video [AB][^\]]*\])/g);
  return (
    <span>
      {parts.map((part, i) =>
        part.match(/^\[Video [AB]/) ? (
          <span key={i} style={citationStyle}>{part}</span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
}

const citationStyle = {
  background: "#1e1030", color: "#a78bfa", fontSize: 11,
  padding: "1px 6px", borderRadius: 4, border: "1px solid #3d1f6e",
  fontFamily: "monospace", marginLeft: 2, marginRight: 2,
};

const styles = {
  wrapper: { margin: "0 40px", background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: 12, display: "flex", flexDirection: "column", overflow: "hidden" },
  panelHeader: { padding: "14px 20px", borderBottom: "1px solid #2a2a2a", display: "flex", alignItems: "center", justifyContent: "space-between" },
  panelTitle: { fontSize: 14, fontWeight: 600, color: "#e0e0e0" },
  streamingBadge: { fontSize: 12, color: "#4ade80", fontWeight: 500 },
  suggestions: { display: "flex", flexWrap: "wrap", gap: 8, padding: "16px 20px", borderBottom: "1px solid #222" },
  chip: { background: "#111", border: "1px solid #2e2e2e", borderRadius: 20, color: "#aaa", fontSize: 12, padding: "6px 14px", cursor: "pointer", textAlign: "left" },
  messages: { flex: 1, minHeight: 300, maxHeight: 480, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 },
  msgRow: { display: "flex" },
  bubble: { maxWidth: "80%", padding: "10px 14px", borderRadius: 10, fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word" },
  userBubble: { background: "#7c3aed", color: "#fff", borderBottomRightRadius: 2 },
  aiBubble: { background: "#111", color: "#e0e0e0", border: "1px solid #222", borderBottomLeftRadius: 2 },
  inputRow: { display: "flex", gap: 10, padding: "14px 20px", borderTop: "1px solid #2a2a2a", alignItems: "flex-end" },
  textarea: { flex: 1, background: "#111", border: "1px solid #2e2e2e", borderRadius: 8, padding: "10px 14px", fontSize: 14, color: "#e8e8e8", resize: "none", outline: "none", fontFamily: "inherit", lineHeight: 1.5 },
  sendBtn: { background: "#7c3aed", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer", height: 42 },
};
