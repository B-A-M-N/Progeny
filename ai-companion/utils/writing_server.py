from flask import Flask, request, jsonify, send_from_directory
import os
import json
import base64
import time
import yaml
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
    }

@app.route('/')
def index():
    return send_from_directory(DATA_DIR, 'writing_canvas.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory(DATA_DIR, 'dashboard.html')

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

if __name__ == '__main__':
    # Get local IP for convenience
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    
    print(f"--- Writing Server Started ---")
    print(f"Access on Kindle at: http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000)
