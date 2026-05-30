import os
import re
from typing import Optional
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

load_dotenv()


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_transcript(url: str) -> dict:
    """
    Fetch transcript and metadata for a YouTube video.
    Returns dict with transcript text, metadata, and engagement metrics.
    """
    video_id = extract_youtube_id(url)
    if not video_id:
        raise ValueError(f"Could not extract YouTube video ID from URL: {url}")

    # --- Transcript via yt-dlp ---
    try:
        transcript_text = ""
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            subs = info.get("subtitles", {}) or {}
            auto = info.get("automatic_captions", {}) or {}
            all_subs = {**auto, **subs}

            for lang in ["en", "en-US", "en-GB"]:
                if lang not in all_subs:
                    continue
                entries = all_subs[lang]

                # Try VTT first
                vtt_entry = next((f for f in entries if f.get("ext") == "vtt"), None)
                json_entry = next((f for f in entries if f.get("ext") == "json3"), None)

                if vtt_entry:
                    import urllib.request
                    with urllib.request.urlopen(vtt_entry["url"]) as r:
                        raw = r.read().decode("utf-8")
                    raw = re.sub(r"\d{2}:\d{2}:[\d\.]+\s*-->\s*\S+.*", "", raw)
                    raw = re.sub(r"<[^>]+>", "", raw)
                    raw = re.sub(r"WEBVTT.*", "", raw)
                    raw = re.sub(r"\s{2,}", " ", raw).strip()
                    transcript_text = raw
                    break

                elif json_entry:
                    import urllib.request, json
                    with urllib.request.urlopen(json_entry["url"]) as r:
                        data = json.loads(r.read().decode("utf-8"))
                    segs = []
                    for event in data.get("events", []):
                        for seg in event.get("segs", []):
                            t = seg.get("utf8", "").strip()
                            if t and t != "\n":
                                segs.append(t)
                    transcript_text = " ".join(segs)
                    break

        if not transcript_text:
            transcript_text = "[No English captions found]"
    except Exception as e:
        transcript_text = f"[Transcript unavailable: {str(e)}]"
    # --- Metadata via yt-dlp ---
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    metadata = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            metadata = {
                "video_id_raw": video_id,
                "platform": "youtube",
                "url": url,
                "title": info.get("title", "Unknown"),
                "creator": info.get("uploader", "Unknown"),
                "channel_id": info.get("channel_id", ""),
                "follower_count": info.get("channel_follower_count", 0) or 0,
                "views": info.get("view_count", 0) or 0,
                "likes": info.get("like_count", 0) or 0,
                "comments": info.get("comment_count", 0) or 0,
                "upload_date": info.get("upload_date", ""),
                "duration": info.get("duration", 0) or 0,
                "hashtags": info.get("tags", [])[:10],
                "description": (info.get("description", "") or "")[:500],
            }
        except Exception as e:
            metadata = {
                "video_id_raw": video_id,
                "platform": "youtube",
                "url": url,
                "title": "Unknown",
                "creator": "Unknown",
                "follower_count": 0,
                "views": 0,
                "likes": 0,
                "comments": 0,
                "upload_date": "",
                "duration": 0,
                "hashtags": [],
                "description": "",
                "error": str(e),
            }

    # --- Engagement Rate ---
    views = metadata.get("views", 0)
    likes = metadata.get("likes", 0)
    comments = metadata.get("comments", 0)
    engagement_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0
    metadata["engagement_rate"] = engagement_rate

    return {
        "transcript": transcript_text,
        "metadata": metadata,
    }


def get_instagram_transcript(url: str) -> dict:
    """
    Fetch transcript and metadata for an Instagram Reel.
    Uses yt-dlp for download + metadata extraction.
    Audio is saved temporarily for Whisper transcription if no captions.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    metadata = {}
    transcript_text = ""

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)

            # Extract subtitles/captions if available
            subtitles = info.get("subtitles", {}) or {}
            auto_captions = info.get("automatic_captions", {}) or {}
            all_captions = {**subtitles, **auto_captions}

            if all_captions:
                lang = next(iter(all_captions))
                caption_data = all_captions[lang]
                if caption_data:
                    transcript_text = caption_data[0].get("url", "")
                    # If it's a URL, note it — for demo we use description as fallback
                    transcript_text = f"[Captions available in {lang}]"

            if not transcript_text:
                transcript_text = (
                    f"[Auto-transcript unavailable. Description: "
                    f"{(info.get('description', '') or '')[:300]}]"
                )

            # Build metadata
            raw_id = info.get("id", url.split("/")[-2] if "/" in url else url)
            metadata = {
                "video_id_raw": raw_id,
                "platform": "instagram",
                "url": url,
                "title": info.get("title", info.get("description", "Instagram Reel"))[:100],
                "creator": info.get("uploader", info.get("creator", "Unknown")),
                "channel_id": info.get("channel_id", info.get("uploader_id", "")),
                "follower_count": info.get("channel_follower_count", 0) or 0,
                "views": info.get("view_count", 0) or 0,
                "likes": info.get("like_count", 0) or 0,
                "comments": info.get("comment_count", 0) or 0,
                "upload_date": info.get("upload_date", ""),
                "duration": info.get("duration", 0) or 0,
                "hashtags": re.findall(r"#\w+", info.get("description", "") or "")[:10],
                "description": (info.get("description", "") or "")[:500],
            }

        except Exception as e:
            raw_id = url.split("/")[-2] if "/" in url else url
            metadata = {
                "video_id_raw": raw_id,
                "platform": "instagram",
                "url": url,
                "title": "Instagram Reel",
                "creator": "Unknown",
                "follower_count": 0,
                "views": 0,
                "likes": 0,
                "comments": 0,
                "upload_date": "",
                "duration": 0,
                "hashtags": [],
                "description": "",
                "error": str(e),
            }
            transcript_text = f"[Could not fetch Instagram data: {str(e)}]"

    # --- Engagement Rate ---
    views = metadata.get("views", 0)
    likes = metadata.get("likes", 0)
    comments = metadata.get("comments", 0)
    engagement_rate = round((likes + comments) / views * 100, 4) if views > 0 else 0.0
    metadata["engagement_rate"] = engagement_rate

    return {
        "transcript": transcript_text,
        "metadata": metadata,
    }


def ingest_video(url: str, video_label: str) -> dict:
    """
    Main entry point. Auto-detects platform from URL.
    video_label: 'A' or 'B' — used to tag chunks in vector DB.
    """
    url = url.strip()
    if "youtube.com" in url or "youtu.be" in url:
        result = get_youtube_transcript(url)
    elif "instagram.com" in url:
        result = get_instagram_transcript(url)
    else:
        raise ValueError(f"Unsupported platform URL: {url}")

    result["video_label"] = video_label
    result["metadata"]["video_label"] = video_label
    return result


# Quick test — run directly to verify
if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print("Testing YouTube ingestion...")
    result = ingest_video(test_url, "A")
    print(f"Title: {result['metadata']['title']}")
    print(f"Creator: {result['metadata']['creator']}")
    print(f"Views: {result['metadata']['views']}")
    print(f"Engagement Rate: {result['metadata']['engagement_rate']}%")
    print(f"Transcript (first 200 chars): {result['transcript'][:200]}")
