# Observation Pipeline: Turning Footage Into Child Profile Data

---

## The Actual Concept

You are not teaching AI to understand video like a human does. You are extracting three simple numbers from video, logging them over time, and finding patterns in those numbers. That's the whole thing.

The three numbers you need:

| Signal | What it is | How you get it |
|--------|-----------|----------------|
| **Present** | Is he in the room right now | MediaPipe face detector: yes/no |
| **Attention** | Is he facing the screen | MediaPipe head pose: forward/away/down |
| **Activity** | How much is he moving | OpenCV optical flow: 0.0 to 1.0 |

For screen content you don't need video analysis at all. Python reads the active window title every 30 seconds. If he's watching YouTube in Chrome, the window title is the video title. That's your content log.

Every signal gets timestamped and written to a file. At the end of each day a summarizer reads all of it, finds patterns, and writes a profile entry to Postgres. Bitling reads those profile entries when it starts.

---

## What You're Not Doing

- You are not running facial expression recognition
- You are not doing emotion detection from video
- You are not analyzing audio for this phase
- You are not screen recording video files (just reading window titles)
- You are not doing anything that requires the GPU

The 5900x handles all of this comfortably. MediaPipe face detection on a 720p webcam feed runs at roughly 15–20fps on CPU. You don't need real-time — you can process at 2fps and get everything you need.

---

## The Tool Stack

Everything here installs with pip. No CUDA, no special drivers, no model downloads beyond what pip handles automatically.

```bash
pip install mediapipe opencv-python numpy psycopg2-binary pygetwindow
```

On Linux, window title reading uses `xdotool` instead of pygetwindow:

```bash
sudo apt install xdotool
```

MediaPipe ships with its own lightweight face detection and face mesh models. They download automatically on first run and are small (a few MB). No Ollama, no LLM, no GPU — just MediaPipe doing geometry math on your CPU.

---

## The Three Scripts

### Script 1: webcam_observer.py

Reads from the webcam continuously during observation hours. Writes one line of JSON per second to a rolling log file.

```python
import cv2
import mediapipe as mp
import numpy as np
import json
import time
from datetime import datetime
from pathlib import Path

# MediaPipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def estimate_head_pose(landmarks, frame_w, frame_h):
    """
    Returns rough attention direction from facial landmark geometry.
    'forward' = facing screen, 'away' = turned away, 'down' = looking at tablet/lap.
    Not precise — just a useful proxy.
    """
    nose_tip = landmarks[4]
    left_eye = landmarks[33]
    right_eye = landmarks[263]

    # Horizontal: nose relative to eye midpoint
    eye_mid_x = (left_eye.x + right_eye.x) / 2
    h_offset = nose_tip.x - eye_mid_x

    # Vertical: nose y relative to eye y
    eye_mid_y = (left_eye.y + right_eye.y) / 2
    v_offset = nose_tip.y - eye_mid_y

    if abs(h_offset) > 0.08:
        return "away"
    elif v_offset > 0.06:
        return "down"
    else:
        return "forward"

def compute_activity(prev_frame, curr_frame):
    """
    Optical flow magnitude as a 0.0-1.0 activity score.
    Low = sitting still. High = moving around.
    """
    if prev_frame is None:
        return 0.0
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        0.5, 3, 15, 3, 5, 1.2, 0
    )
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    score = float(np.mean(magnitude))
    # Normalize roughly: 0-5 is normal range, cap at 1.0
    return min(score / 5.0, 1.0)

def run_observer(output_dir="data/observations", sample_every_n_frames=15):
    """
    Main loop. Reads webcam, extracts signals, writes one JSON line per sample.
    sample_every_n_frames=15 at 30fps = 2 samples per second. Adjust to taste.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path(output_dir) / f"webcam_{today}.jsonl"

    prev_frame = None
    frame_count = 0

    print(f"Observer running. Writing to {log_path}. Ctrl+C to stop.")

    with open(log_path, "a") as f:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame_count += 1
            if frame_count % sample_every_n_frames != 0:
                prev_frame = frame.copy()
                continue

            ts = datetime.now().isoformat()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)

            present = result.multi_face_landmarks is not None
            attention = "unknown"
            activity = compute_activity(prev_frame, frame)

            if present:
                lms = result.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]
                attention = estimate_head_pose(lms, w, h)

            record = {
                "ts": ts,
                "present": present,
                "attention": attention,
                "activity": round(activity, 3)
            }

            f.write(json.dumps(record) + "\n")
            f.flush()

            prev_frame = frame.copy()

    cap.release()

if __name__ == "__main__":
    run_observer()
```

**What the output looks like** (`webcam_2026-03-07.jsonl`):

```json
{"ts": "2026-03-07T14:03:22.441", "present": true, "attention": "forward", "activity": 0.12}
{"ts": "2026-03-07T14:03:29.882", "present": true, "attention": "down", "activity": 0.08}
{"ts": "2026-03-07T14:03:37.301", "present": false, "attention": "unknown", "activity": 0.31}
{"ts": "2026-03-07T14:03:44.715", "present": true, "attention": "forward", "activity": 0.19}
```

---

### Script 2: content_logger.py

Reads the active window title every 30 seconds. On Linux this uses `xdotool`. This is your content log — no screen recording needed.

```python
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

def get_active_window_title():
    """
    Get the title of the currently focused window.
    On Linux with X11. Returns empty string on failure.
    """
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip()
    except Exception:
        return ""

def classify_content(title):
    """
    Rough content type from window title keywords.
    Add whatever categories make sense for what he actually watches.
    """
    title_lower = title.lower()

    categories = {
        "youtube": ["youtube", "youtu.be"],
        "netflix": ["netflix"],
        "dinosaur": ["dinosaur", "dino", "t-rex", "trex", "jurassic"],
        "vehicles": ["truck", "car", "train", "tractor", "excavator", "bulldozer"],
        "gaming": ["minecraft", "roblox", "fortnite", "game"],
        "educational": ["pbs", "sesame", "bluey", "ms. rachel", "cocomelon"],
        "music": ["music", "songs", "nursery"],
    }

    matched = []
    for category, keywords in categories.items():
        if any(kw in title_lower for kw in keywords):
            matched.append(category)

    return matched if matched else ["other"]

def run_content_logger(output_dir="data/observations", interval_seconds=30):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path(output_dir) / f"content_{today}.jsonl"

    print(f"Content logger running. Writing to {log_path}. Ctrl+C to stop.")

    last_title = None

    with open(log_path, "a") as f:
        while True:
            title = get_active_window_title()
            ts = datetime.now().isoformat()

            # Always log, but mark if it changed
            changed = title != last_title
            categories = classify_content(title)

            record = {
                "ts": ts,
                "title": title,
                "categories": categories,
                "changed": changed
            }

            f.write(json.dumps(record) + "\n")
            f.flush()

            last_title = title
            time.sleep(interval_seconds)

if __name__ == "__main__":
    run_content_logger()
```

**What the output looks like** (`content_2026-03-07.jsonl`):

```json
{"ts": "2026-03-07T14:03:00.001", "title": "Blippi Visits a Dinosaur Museum - YouTube", "categories": ["youtube", "dinosaur", "educational"], "changed": true}
{"ts": "2026-03-07T14:03:30.002", "title": "Blippi Visits a Dinosaur Museum - YouTube", "categories": ["youtube", "dinosaur", "educational"], "changed": false}
{"ts": "2026-03-07T14:04:00.003", "title": "Monster Trucks for Kids - YouTube", "categories": ["youtube", "vehicles"], "changed": true}
```

---

### Script 3: daily_summarizer.py

Runs once at the end of the day (or overnight via cron). Reads both log files, correlates them, writes a summary to Postgres.

```python
import json
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

def load_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records

def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str)

def bucket_by_minute(records, key_fn):
    """Groups records into 1-minute buckets, applying key_fn to each."""
    buckets = defaultdict(list)
    for r in records:
        minute = parse_ts(r["ts"]).replace(second=0, microsecond=0)
        buckets[minute].append(key_fn(r))
    return buckets

def summarize_day(date_str, obs_dir="data/observations"):
    webcam_path = Path(obs_dir) / f"webcam_{date_str}.jsonl"
    content_path = Path(obs_dir) / f"content_{date_str}.jsonl"

    if not webcam_path.exists():
        print(f"No webcam data for {date_str}")
        return None

    webcam = load_jsonl(webcam_path)
    content = load_jsonl(content_path) if content_path.exists() else []

    # --- Webcam analysis ---

    present_records = [r for r in webcam if r["present"]]
    total_records = len(webcam)

    presence_rate = len(present_records) / total_records if total_records else 0

    attention_counts = Counter(r["attention"] for r in present_records)
    forward_rate = attention_counts.get("forward", 0) / len(present_records) if present_records else 0
    down_rate = attention_counts.get("down", 0) / len(present_records) if present_records else 0

    activity_scores = [r["activity"] for r in present_records]
    avg_activity = sum(activity_scores) / len(activity_scores) if activity_scores else 0

    # Find continuous presence windows (gaps > 5 min = new window)
    presence_windows = []
    window_start = None
    last_present_ts = None

    for r in sorted(webcam, key=lambda x: x["ts"]):
        ts = parse_ts(r["ts"])
        if r["present"]:
            if window_start is None:
                window_start = ts
            last_present_ts = ts
        else:
            if window_start and last_present_ts:
                gap = (ts - last_present_ts).total_seconds()
                if gap > 300:  # 5 minute gap = new window
                    duration = (last_present_ts - window_start).total_seconds() / 60
                    if duration >= 2:  # only count windows > 2 min
                        presence_windows.append({
                            "start": window_start.isoformat(),
                            "end": last_present_ts.isoformat(),
                            "duration_minutes": round(duration, 1)
                        })
                    window_start = None
                    last_present_ts = None

    avg_session_minutes = (
        sum(w["duration_minutes"] for w in presence_windows) / len(presence_windows)
        if presence_windows else 0
    )

    # Peak hours: which hours had highest presence rate
    hourly_presence = defaultdict(list)
    for r in webcam:
        hour = parse_ts(r["ts"]).hour
        hourly_presence[hour].append(r["present"])

    peak_hours = sorted(
        [(h, sum(v)/len(v)) for h, v in hourly_presence.items()],
        key=lambda x: x[1], reverse=True
    )[:3]

    # --- Content analysis ---

    category_presence = defaultdict(int)  # category -> minutes with presence

    if content:
        # For each content record, find webcam state around same timestamp
        webcam_by_minute = bucket_by_minute(
            webcam,
            lambda r: r["present"]
        )

        for cr in content:
            minute = parse_ts(cr["ts"]).replace(second=0, microsecond=0)
            presence_in_minute = webcam_by_minute.get(minute, [])
            if any(presence_in_minute):
                for cat in cr["categories"]:
                    category_presence[cat] += 1

    top_content = sorted(category_presence.items(), key=lambda x: x[1], reverse=True)[:5]

    # --- Build summary ---

    summary = {
        "date": date_str,
        "presence_rate": round(presence_rate, 3),
        "forward_attention_rate": round(forward_rate, 3),
        "tablet_attention_rate": round(down_rate, 3),
        "avg_activity_level": round(avg_activity, 3),
        "avg_session_minutes": round(avg_session_minutes, 1),
        "session_count": len(presence_windows),
        "peak_hours": [h for h, _ in peak_hours],
        "top_content_categories": [cat for cat, _ in top_content],
        "presence_windows": presence_windows
    }

    return summary

def write_to_postgres(summary, db_url):
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS observation_days (
            date DATE PRIMARY KEY,
            presence_rate FLOAT,
            forward_attention_rate FLOAT,
            tablet_attention_rate FLOAT,
            avg_activity_level FLOAT,
            avg_session_minutes FLOAT,
            session_count INT,
            peak_hours JSONB,
            top_content_categories JSONB,
            presence_windows JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        INSERT INTO observation_days (
            date, presence_rate, forward_attention_rate, tablet_attention_rate,
            avg_activity_level, avg_session_minutes, session_count,
            peak_hours, top_content_categories, presence_windows
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            presence_rate = EXCLUDED.presence_rate,
            forward_attention_rate = EXCLUDED.forward_attention_rate,
            tablet_attention_rate = EXCLUDED.tablet_attention_rate,
            avg_activity_level = EXCLUDED.avg_activity_level,
            avg_session_minutes = EXCLUDED.avg_session_minutes,
            session_count = EXCLUDED.session_count,
            peak_hours = EXCLUDED.peak_hours,
            top_content_categories = EXCLUDED.top_content_categories,
            presence_windows = EXCLUDED.presence_windows
    """, (
        summary["date"],
        summary["presence_rate"],
        summary["forward_attention_rate"],
        summary["tablet_attention_rate"],
        summary["avg_activity_level"],
        summary["avg_session_minutes"],
        summary["session_count"],
        json.dumps(summary["peak_hours"]),
        json.dumps(summary["top_content_categories"]),
        json.dumps(summary["presence_windows"])
    ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"Written summary for {summary['date']} to Postgres.")

if __name__ == "__main__":
    import sys
    import os

    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/progeny")

    summary = summarize_day(date_str)
    if summary:
        print(json.dumps(summary, indent=2))
        write_to_postgres(summary, db_url)
```

---

## Running It

Two terminals during observation days, one cron job at night.

**Terminal 1 — webcam:**
```bash
source ai-companion/venv/bin/activate
python ai-companion/utils/webcam_observer.py
```

**Terminal 2 — content:**
```bash
source ai-companion/venv/bin/activate
python ai-companion/utils/content_logger.py
```

**Nightly cron — runs at 11pm, summarizes the day:**
```bash
crontab -e
```
Add:
```
0 23 * * * cd /home/bamn/Progeny && source ai-companion/venv/bin/activate && python ai-companion/utils/daily_summarizer.py >> logs/observation_summary.log 2>&1
```

You can also run the summarizer manually at any point:
```bash
python ai-companion/utils/daily_summarizer.py 2026-03-07
```

---

## What the Summary Looks Like

After one day of observation, the daily summarizer produces something like this:

```json
{
  "date": "2026-03-07",
  "presence_rate": 0.61,
  "forward_attention_rate": 0.74,
  "tablet_attention_rate": 0.19,
  "avg_activity_level": 0.23,
  "avg_session_minutes": 18.4,
  "session_count": 3,
  "peak_hours": [15, 19, 14],
  "top_content_categories": ["youtube", "dinosaur", "vehicles", "educational", "gaming"],
  "presence_windows": [
    {"start": "2026-03-07T14:02:00", "end": "2026-03-07T14:38:00", "duration_minutes": 36.1},
    {"start": "2026-03-07T15:45:00", "end": "2026-03-07T16:03:00", "duration_minutes": 18.0},
    {"start": "2026-03-07T19:12:00", "end": "2026-03-07T19:28:00", "duration_minutes": 16.3}
  ]
}
```

Read it like this:

- **presence_rate 0.61** — he was in the room about 60% of observed time
- **forward_attention_rate 0.74** — when present, he was facing the TV 74% of the time
- **tablet_attention_rate 0.19** — 19% of the time he was looking down (tablet, lap, floor)
- **avg_activity_level 0.23** — mostly calm/still (0 = statue, 1 = constant movement)
- **avg_session_minutes 18.4** — his natural session length before leaving the room is about 18 minutes
- **peak_hours [15, 19, 14]** — most present at 3pm, then 7pm, then 2pm
- **top_content_categories** — he watched dinosaur and vehicle content most while present

After 7 days, you average these across the week. Patterns emerge fast. You'll see which hours he's reliably available, how long he sustains attention, whether he's a morning kid or afternoon kid, and what content categories track with his highest presence and forward attention rates. That's the input to Bitling's initial profile.

---

## After the Observation Week: Feeding Bitling

When the first contact phase begins, the brain reads the observation profile from Postgres to initialize the child's adaptive state:

```python
def load_observation_profile(db_url, days=7):
    """
    Averages the last N days of observation summaries into
    a starting profile for the adaptive engines.
    """
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            AVG(presence_rate) as avg_presence,
            AVG(forward_attention_rate) as avg_forward,
            AVG(tablet_attention_rate) as avg_tablet,
            AVG(avg_activity_level) as avg_activity,
            AVG(avg_session_minutes) as avg_session_len,
            AVG(session_count) as avg_daily_sessions
        FROM observation_days
        WHERE date >= NOW() - INTERVAL '%s days'
    """, (days,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or row[0] is None:
        return None

    return {
        "baseline_attention_span_minutes": round(row[4], 1),
        "typical_daily_sessions": round(row[5], 1),
        "activity_level": "high" if row[3] > 0.4 else "moderate" if row[3] > 0.2 else "calm",
        "screen_vs_tablet_split": round(row[1], 2),  # forward attention rate
        "estimated_peak_availability": "afternoon",   # from peak_hours — refine this
    }
```

This profile gets stored on the child record in Postgres and seeded into the adaptive state on first session. Instead of starting with defaults, Bitling knows approximately how long this specific kid can sit before needing a break, what time of day he's most receptive, and how calm or active his baseline state is.

---

## What to Do If the Webcam Has a Bad Angle

If the webcam doesn't have a clean view of his face (behind him, off to the side, too far), the face detection accuracy drops significantly. In that case:

**Fall back to motion-only observation:**
Skip the face mesh entirely. Just run optical flow across the full frame. You lose attention direction but keep presence estimation (someone in the room = motion changes) and activity level. Still useful for session timing and energy patterns.

**Adjust the camera first.** A webcam positioned roughly at TV height and centered gets the most useful data. It doesn't need to be hidden — he probably won't care about a webcam sitting near the TV and you don't need to explain it.

---

## Privacy Note

All footage and extracted data stays local. The `.jsonl` files go in `data/observations/` which is already in `.gitignore` territory given Progeny's local-first stance. No frames are sent anywhere. MediaPipe processes frames in memory and the frames are discarded immediately — only the extracted signal numbers are written to disk. If you want to be extra clean, delete the raw `.jsonl` files after the daily summarizer runs. The summary in Postgres is all you need.

---

*Pipeline document for Progeny observation week. March 2026.*
