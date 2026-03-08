from flask import Flask, request, jsonify, send_from_directory, send_file
import os
import json
import base64
import time
import yaml
import io
import urllib.parse
import socket
from services.memory_service import MemoryService
from services.onboarding_service import OnboardingService

app = Flask(__name__)

# Config
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "writing_samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

# Shared Memory Service
memory = MemoryService()
cfg = {}
config_path = os.path.join(PROJECT_ROOT, "config.yaml")
if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}
onboarding = OnboardingService(memory, cfg)
active_media_sessions = {}


def _detect_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip


def _compute_stroke_metrics(strokes):
    all_points = [p for s in strokes for p in s if isinstance(p, dict)]
    if not all_points:
        return {}
    pressures = [float(p.get('p', 0.5)) for p in all_points]
    times = [float(p.get('t', 0)) for p in all_points]
    stroke_lengths = [len(s) for s in strokes if isinstance(s, list)]
    pressure_mean = sum(pressures) / len(pressures)
    pressure_var = sum((x - pressure_mean) ** 2 for x in pressures) / max(1, len(pressures))
    spike_count = sum(1 for i in range(1, len(pressures)) if (pressures[i] - pressures[i - 1]) > 0.25)
    pressure_spike_frequency = spike_count / max(1, len(pressures) - 1)
    micro_pause_count = 0
    for i in range(1, len(times)):
        if (times[i] - times[i - 1]) > 350:
            micro_pause_count += 1
    avg_points_per_stroke = (sum(stroke_lengths) / max(1, len(stroke_lengths)))
    stroke_fragmentation = 1.0 / max(1.0, avg_points_per_stroke)
    engagement_duration = max(0.0, (max(times) - min(times)) / 1000.0)
    return {
        "pressure_mean": round(pressure_mean, 4),
        "pressure_variance": round(pressure_var, 4),
        "pressure_spike_frequency": round(pressure_spike_frequency, 4),
        "micro_pause_count": micro_pause_count,
        "stroke_count": len(stroke_lengths),
        "stroke_fragmentation": round(stroke_fragmentation, 4),
        "engagement_duration": round(engagement_duration, 4),
        "signals": {
            "micro_frustration": round(min(1.0, pressure_spike_frequency), 4),
            "task_abandonment": 1.0 if len(stroke_lengths) <= 1 else 0.0,
            "movement_acceleration": round(min(1.0, pressure_var * 2.0), 4),
        }
    }

@app.route('/')
def index():
    return send_from_directory(DATA_DIR, 'writing_canvas.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory(DATA_DIR, 'dashboard.html')


@app.route('/api/writing/qr', methods=['GET'])
def writing_qr():
    target = request.args.get("target", "").strip()
    if target == "":
        local_ip = _detect_local_ip()
        target = f"http://{local_ip}:5000/"
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(target)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except Exception:
        escaped = urllib.parse.quote(target, safe="")
        html = (
            "<html><body style='font-family:sans-serif;padding:24px;'>"
            "<h2>Writing Pad Link</h2>"
            f"<p><a href='{target}'>{target}</a></p>"
            f"<p>Install qrcode+pillow for PNG QR output.</p>"
            f"<p>Encoded: {escaped}</p>"
            "</body></html>"
        )
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route('/api/struggles')
def get_struggles():
    res = memory.get_unresolved_struggles()
    return jsonify(res)

@app.route('/api/graph_stats')
def get_graph_stats():
    conn = memory.get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT count(*) FROM nodes')
    node_count = cursor.fetchone()[0]
    cursor.execute('SELECT count(*) FROM edges')
    edge_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return jsonify({"nodes": node_count, "edges": edge_count})

@app.route('/api/submit_writing', methods=['POST'])
def submit_writing():
    data = request.json
    image_b64 = data.get('image')
    strokes = data.get('strokes', [])
    
    timestamp = int(time.time())
    filename = f"writing_{timestamp}.png"
    filepath = os.path.join(SAMPLES_DIR, filename)
    
    # 1. Save Image
    try:
        header, encoded = image_b64.split(",", 1)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(encoded))
    except Exception as e:
        return jsonify({"success": False, "message": f"Save failed: {str(e)}"}), 500

    # 2. Analyze Pressure Regulation
    all_points = [p for s in strokes for p in s]
    metrics = _compute_stroke_metrics(strokes)
    if all_points:
        pressures = [p['p'] for p in all_points]
        avg_pressure = sum(pressures) / len(pressures)
        max_pressure = max(pressures)
        
        # Heuristic for pressure regulation
        status = "Good"
        xp_earned = 5 # Base effort
        
        if avg_pressure > 0.8:
            status = "Too Heavy"
            memory.record_event("struggle_detected", "Child is applying excessive pressure while writing.", {}, None, metadata={"avg_p": avg_pressure})
        elif avg_pressure < 0.2:
            status = "Too Light"
            memory.record_event("struggle_detected", "Child is applying very light pressure while writing.", {}, None, metadata={"avg_p": avg_pressure})
        else:
            # Good regulation! Award extra XP
            xp_earned += 10
            memory.log_xp_event("MASTERY", 10, evidence=f"Great pressure regulation (Avg: {avg_pressure:.2f})")

        # Log completion
        memory.log_xp_event("EFFORT", xp_earned, evidence=f"Completed writing sample: {filename}")
        memory.record_event(
            "writing_metrics",
            "Writing pad metrics captured.",
            {},
            None,
            metadata={"filename": filename, "metrics": metrics}
        )
        onboarding.apply_runtime_metrics(metrics)
        if isinstance(metrics.get("signals"), dict):
            for sk, sv in metrics["signals"].items():
                memory.record_onboarding_metric("writing_signal", sk, sv, {"source": "writing_pad"})
        
        message = f"Nice job! Pressure was {status}."
    else:
        message = "No drawing detected, but thanks for trying!"

    return jsonify({
        "success": True, 
        "message": message,
        "filename": filename,
        "metrics": metrics,
        "adaptation_profile": onboarding.get_or_init_profile()
    })


@app.route('/api/regulation/signal', methods=['POST'])
def regulation_signal():
    data = request.json or {}
    session_id = str(data.get("session_id", "external_signal"))
    signals = data.get("signals", {})
    if isinstance(signals, dict):
        for sk, sv in signals.items():
            try:
                val = float(sv)
            except Exception:
                continue
            memory.record_onboarding_metric(session_id, sk, val, {"source": "external_signal"})
    return jsonify({"success": True, "recorded": list(signals.keys()) if isinstance(signals, dict) else []})


@app.route('/api/onboarding/baseline', methods=['POST'])
def onboarding_baseline():
    data = request.json or {}
    baseline = data.get("baseline", {})
    profile = onboarding.apply_parent_baseline(baseline)
    return jsonify({
        "success": True,
        "profile": profile,
        "neurodiversity": profile.get("neurodiversity_profile", {})
    })


@app.route('/api/media/start', methods=['POST'])
def media_start():
    data = request.json or {}
    session_id = str(data.get("session_id", f"media_{int(time.time())}"))
    topic = str(data.get("topic", "general"))
    title = str(data.get("title", ""))
    url = str(data.get("url", ""))
    baseline_state = onboarding.estimate_live_state({}, {})
    active_media_sessions[session_id] = {
        "started_at": time.time(),
        "baseline_state": baseline_state,
        "topic": topic
    }
    memory.start_media_session(
        session_id=session_id,
        topic=topic,
        title=title,
        url=url,
        baseline_state=baseline_state,
        metadata=data.get("metadata", {})
    )
    return jsonify({"success": True, "session_id": session_id, "baseline_state": baseline_state})


@app.route('/api/media/probe', methods=['POST'])
def media_probe():
    data = request.json or {}
    session_id = str(data.get("session_id", ""))
    probe_type = str(data.get("probe_type", "choice_recall"))
    response_mode = str(data.get("response_mode", "choice"))
    response_latency = float(data.get("response_latency", 0.0) or 0.0)
    success_score = float(data.get("success_score", 0.5) or 0.5)
    memory.record_media_probe(
        session_id=session_id,
        probe_type=probe_type,
        response_mode=response_mode,
        response_latency=response_latency,
        success_score=success_score,
        metadata=data.get("metadata", {})
    )
    return jsonify({"success": True})


@app.route('/api/media/end', methods=['POST'])
def media_end():
    data = request.json or {}
    session_id = str(data.get("session_id", ""))
    live = active_media_sessions.get(session_id, {})
    baseline_state = live.get("baseline_state", {})
    end_state = onboarding.estimate_live_state({}, {})
    behavior_delta = {
        "frustration": [baseline_state.get("frustration", "none"), end_state.get("frustration", "none")],
        "engagement": [baseline_state.get("engagement", "none"), end_state.get("engagement", "none")]
    }
    watched_seconds = float(data.get("watched_seconds", 0.0) or 0.0)
    if watched_seconds <= 0 and live.get("started_at"):
        watched_seconds = max(0.0, time.time() - float(live.get("started_at")))
    completed = bool(data.get("completed", False))
    memory.end_media_session(
        session_id=session_id,
        watched_seconds=watched_seconds,
        completed=completed,
        end_state=end_state,
        behavior_delta=behavior_delta,
        metadata=data.get("metadata", {})
    )
    topic = live.get("topic") or data.get("topic")
    insight = memory.get_media_effectiveness(topic=topic) if topic else {}
    if session_id in active_media_sessions:
        del active_media_sessions[session_id]
    return jsonify({"success": True, "behavior_delta": behavior_delta, "effectiveness": insight})


@app.route('/api/media/insights', methods=['GET'])
def media_insights():
    topic = request.args.get("topic")
    if topic:
        insights = memory.get_media_effectiveness(topic=topic)
    else:
        insights = memory.get_media_effectiveness(limit=20)
    return jsonify({"success": True, "insights": insights})

if __name__ == '__main__':
    # Get local IP for convenience
    import socket
    local_ip = _detect_local_ip()
    
    print(f"--- Writing Server Started ---")
    print(f"Access on Kindle at: http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000)
