export default function VideoCard({ video, label }) {
  if (!video) return null;

  const eng = parseFloat(video.engagement_rate) || 0;
  const engagementColor = eng > 5 ? "#4ade80" : eng > 2 ? "#facc15" : "#f87171";

  const formatNum = (n) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return n?.toString() || "0";
  };

  const formatDate = (d) => {
    if (!d || d.length !== 8) return d || "-";
    return d.slice(0,4) + "-" + d.slice(4,6) + "-" + d.slice(6,8);
  };

  const formatDuration = (secs) => {
    if (!secs) return "-";
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m + ":" + s.toString().padStart(2, "0");
  };

  const labelColor = label === "A" ? "#7c3aed" : "#0ea5e9";
  const platformColor = video.platform === "youtube" ? "#ff4444" : "#c13584";

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={{ ...styles.labelBadge, background: labelColor }}>Video {label}</span>
        <span style={{ ...styles.platformBadge, background: platformColor }}>
          {video.platform === "youtube" ? "YouTube" : "Instagram"}
        </span>
      </div>
      <h3 style={styles.title}>
        {video.title?.length > 60 ? video.title.slice(0, 60) + "..." : video.title}
      </h3>
      <p style={styles.creator}>by {video.creator}</p>
      <div style={styles.engagementBox}>
        <span style={styles.engLabel}>Engagement Rate</span>
        <span style={{ ...styles.engValue, color: engagementColor }}>
          {video.engagement_rate?.toFixed(3)}%
        </span>
      </div>
      <div style={styles.statsGrid}>
        <Stat label="Views" value={formatNum(video.views)} />
        <Stat label="Likes" value={formatNum(video.likes)} />
        <Stat label="Comments" value={formatNum(video.comments)} />
        <Stat label="Followers" value={formatNum(video.follower_count)} />
        <Stat label="Duration" value={formatDuration(video.duration)} />
        <Stat label="Uploaded" value={formatDate(video.upload_date)} />
      </div>
      {video.hashtags && (
        <div style={styles.hashtagRow}>
          {(Array.isArray(video.hashtags) ? video.hashtags : (video.hashtags || "").split(", ")).filter(Boolean).slice(0, 5).map((tag) => (
            <span key={tag} style={styles.hashtag}>#{tag.replace("#", "")}</span>
          ))}
        </div>
      )}
      <a href={video.url} target="_blank" rel="noreferrer" style={styles.link}>Open video</a>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={statStyles.box}>
      <span style={statStyles.label}>{label}</span>
      <span style={statStyles.value}>{value}</span>
    </div>
  );
}

const styles = {
  card: { flex: 1, minWidth: 280, background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: 12, padding: 20, display: "flex", flexDirection: "column", gap: 12 },
  header: { display: "flex", gap: 8, alignItems: "center" },
  labelBadge: { fontSize: 11, fontWeight: 700, color: "#fff", padding: "3px 10px", borderRadius: 20 },
  platformBadge: { fontSize: 11, fontWeight: 500, color: "#fff", padding: "3px 10px", borderRadius: 20 },
  title: { fontSize: 15, fontWeight: 600, color: "#f0f0f0", margin: 0, lineHeight: 1.4 },
  creator: { fontSize: 13, color: "#888", margin: 0 },
  engagementBox: { background: "#111", borderRadius: 8, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #222" },
  engLabel: { fontSize: 12, color: "#666", fontWeight: 500 },
  engValue: { fontSize: 22, fontWeight: 700 },
  statsGrid: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 },
  hashtagRow: { display: "flex", flexWrap: "wrap", gap: 6 },
  hashtag: { fontSize: 11, color: "#7c3aed", background: "#1e1030", padding: "2px 8px", borderRadius: 20, border: "1px solid #3d1f6e" },
  link: { fontSize: 12, color: "#7c3aed", textDecoration: "none", marginTop: 4 },
};

const statStyles = {
  box: { background: "#111", borderRadius: 6, padding: "8px 10px", display: "flex", flexDirection: "column", gap: 2, border: "1px solid #1e1e1e" },
  label: { fontSize: 10, color: "#555", textTransform: "uppercase", letterSpacing: "0.05em" },
  value: { fontSize: 14, fontWeight: 600, color: "#e0e0e0" },
};
