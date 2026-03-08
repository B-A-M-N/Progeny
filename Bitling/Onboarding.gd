extends Control
class_name Onboarding

var socket = WebSocketPeer.new()
var ws_urls: Array = []
var ws_index := 0
var last_state := WebSocketPeer.STATE_CLOSED
var connecting_seconds := 0.0

var session_id := "first_run"
var script_items: Array = []
var script_index := 0
var prompt_started_ms := 0
var warmup_info := {"enabled": false, "active": false, "current_run": 1, "completed_runs": 0, "total_runs": 3}

@onready var status_label = $Root/TopBar/StatusLabel
@onready var tabs = $Root/TabContainer
@onready var parent_notes = $Root/TabContainer/Parent/ParentVBox/NotesField
@onready var interests_field = $Root/TabContainer/Parent/ParentVBox/InterestsField
@onready var save_parent_button = $Root/TabContainer/Parent/ParentVBox/ParentButtons/SaveParentButton
@onready var begin_child_button = $Root/TabContainer/Parent/ParentVBox/ParentButtons/BeginChildButton
@onready var go_main_button = $Root/TabContainer/Parent/ParentVBox/ParentButtons/GoMainButton
@onready var parent_summary = $Root/TabContainer/Parent/ParentVBox/Summary
@onready var warmup_toggle = $Root/TabContainer/Parent/ParentVBox/WarmupToggle
@onready var warmup_track = $Root/TabContainer/Parent/ParentVBox/WarmupTrack
@onready var warmup_dot_1 = $Root/TabContainer/Parent/ParentVBox/WarmupTrack/Dot1
@onready var warmup_dot_2 = $Root/TabContainer/Parent/ParentVBox/WarmupTrack/Dot2
@onready var warmup_dot_3 = $Root/TabContainer/Parent/ParentVBox/WarmupTrack/Dot3

@onready var age_spin = $Root/TabContainer/Parent/ParentVBox/Grid/AgeSpin
@onready var comm_mode = $Root/TabContainer/Parent/ParentVBox/Grid/CommMode
@onready var sound_sens = $Root/TabContainer/Parent/ParentVBox/Grid/SoundSens
@onready var visual_sens = $Root/TabContainer/Parent/ParentVBox/Grid/VisualSens
@onready var latency_pref = $Root/TabContainer/Parent/ParentVBox/Grid/LatencyPref
@onready var literalness_pref = $Root/TabContainer/Parent/ParentVBox/Grid/LiteralnessPref
@onready var demand_pref = $Root/TabContainer/Parent/ParentVBox/Grid/DemandPref
@onready var recovery_pref = $Root/TabContainer/Parent/ParentVBox/Grid/RecoveryPref
@onready var autism_slider = $Root/TabContainer/Parent/ParentVBox/Traits/AutismSlider
@onready var adhd_slider = $Root/TabContainer/Parent/ParentVBox/Traits/ADHDSlider

@onready var child_prompt = $Root/TabContainer/Child/ChildVBox/Prompt
@onready var option_a = $Root/TabContainer/Child/ChildVBox/OptionRow/OptionA
@onready var option_b = $Root/TabContainer/Child/ChildVBox/OptionRow/OptionB
@onready var option_c = $Root/TabContainer/Child/ChildVBox/OptionRow/OptionC
@onready var next_button = $Root/TabContainer/Child/ChildVBox/FlowButtons/NextButton
@onready var skip_button = $Root/TabContainer/Child/ChildVBox/FlowButtons/SkipButton
@onready var finish_button = $Root/TabContainer/Child/ChildVBox/FlowButtons/FinishButton
@onready var child_hint = $Root/TabContainer/Child/ChildVBox/Hint

func _ready():
	_build_ws_urls()
	_connect_ws()
	if save_parent_button:
		save_parent_button.pressed.connect(_on_save_parent_pressed)
	if begin_child_button:
		begin_child_button.pressed.connect(_on_begin_child_pressed)
	if go_main_button:
		go_main_button.pressed.connect(func(): get_tree().change_scene_to_file("res://Main.tscn"))
	if option_a:
		option_a.pressed.connect(func(): _on_child_option("A"))
	if option_b:
		option_b.pressed.connect(func(): _on_child_option("B"))
	if option_c:
		option_c.pressed.connect(func(): _on_child_option("C"))
	if next_button:
		next_button.pressed.connect(_advance_script)
	if skip_button:
		skip_button.pressed.connect(_skip_current)
	if finish_button:
		finish_button.pressed.connect(_finish_onboarding)
	_set_child_controls_enabled(false)
	_update_warmup_hint()
	_set_status("Connecting to brain...")

func _process(delta):
	socket.poll()
	var state = socket.get_ready_state()
	if state == WebSocketPeer.STATE_CONNECTING:
		connecting_seconds += delta
		if connecting_seconds > 2.5:
			socket.close()
	if state != last_state:
		last_state = state
		if state == WebSocketPeer.STATE_OPEN:
			_set_status("Connected. Save parent baseline or begin child session.")
		elif state == WebSocketPeer.STATE_CLOSED:
			ws_index = (ws_index + 1) % max(1, ws_urls.size())
			await get_tree().create_timer(1.0).timeout
			_connect_ws()
	if state == WebSocketPeer.STATE_OPEN:
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			_handle_message(packet.get_string_from_utf8())

func _build_ws_urls():
	ws_urls = []
	for ip in IP.get_local_addresses():
		if ip == "" or ip.find(":") != -1 or ip.begins_with("127."):
			continue
		var c = "ws://" + ip + ":9001/"
		if not ws_urls.has(c):
			ws_urls.append(c)
	ws_urls.append("ws://127.0.0.1:9001/")
	ws_urls.append("ws://localhost:9001/")

func _connect_ws():
	if socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		socket.close()
	socket.supported_protocols = PackedStringArray([])
	connecting_seconds = 0.0
	var url = ws_urls[ws_index] if ws_urls.size() > 0 else "ws://127.0.0.1:9001/"
	print("[Onboarding WS] Connecting to: ", url)
	socket.connect_to_url(url)

func _handle_message(json_str: String):
	var j = JSON.new()
	if j.parse(json_str) != OK:
		return
	var data = j.data
	match str(data.get("type", "")):
		"init":
			_set_status("Brain connected. Ready for onboarding.")
			socket.send_text(JSON.stringify({"type": "get_world_state"}))
			var pad_url = str(data.get("writing_pad_url", ""))
			var pad_qr_url = str(data.get("writing_pad_qr_url", ""))
			if pad_url != "":
				parent_summary.text = "Writing Pad URL (tablet/kindle):\n" + pad_url + "\nWriting Pad QR:\n" + pad_qr_url
		"world_state":
			var trust = data.get("trust_model", {})
			var world = data.get("world_anchor", {})
			var stage = str(trust.get("stage", "safety"))
			var location = str(world.get("location", "world")).replace("_", " ")
			var pad_url = str(data.get("writing_pad_url", ""))
			var pad_qr_url = str(data.get("writing_pad_qr_url", ""))
			parent_summary.text = "Current World: " + location + "\nTrust stage: " + stage + "\nWriting Pad: " + pad_url + "\nWriting QR: " + pad_qr_url
		"onboarding_script":
			script_items = data.get("items", [])
			warmup_info = data.get("warmup", warmup_info)
			script_index = 0
			_set_session_id_for_run()
			_set_child_controls_enabled(script_items.size() > 0)
			_show_current_prompt()
			_update_warmup_hint()
		"onboarding_profile_updated":
			var p = data.get("profile", {})
			warmup_info = data.get("warmup", warmup_info)
			parent_summary.text = "Saved baseline.\nInterests: " + ", ".join(p.get("interest_anchors", []))
			_update_warmup_hint()
		"onboarding_runtime_update":
			var neuro = data.get("neurodiversity", {})
			var style = neuro.get("communication", {}).get("style", "declarative")
			child_hint.text = "Adaptive mode active. Style: " + style
		"onboarding_summary":
			var s = data.get("summary", {})
			var strengths = s.get("strengths", [])
			var friction = s.get("friction_points", [])
			var plan = s.get("starter_plan_7d", [])
			var warm = s.get("warmup", {})
			var trust = data.get("trust_model", {})
			var world = data.get("world_anchor", {})
			warmup_info = data.get("warmup", warmup_info)
			var stage = str(trust.get("stage", "safety"))
			var location = str(world.get("location", "world")).replace("_", " ")
			var warm_msg = str(warm.get("message", ""))
			parent_summary.text = "Session Summary\nWorld: " + location + "\nTrust: " + stage + "\nWarm-up: " + warm_msg + "\n\nStrengths:\n- " + "\n- ".join(strengths) + "\n\nFriction:\n- " + "\n- ".join(friction) + "\n\n7-Day Plan:\n- " + "\n- ".join(plan)
			_update_warmup_hint()
			if tabs:
				tabs.current_tab = 0

func _on_save_parent_pressed():
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		_set_status("Brain not connected.")
		return
	var payload = {
		"type": "set_parent_baseline",
		"baseline": _collect_parent_baseline()
	}
	socket.send_text(JSON.stringify(payload))
	_set_status("Parent baseline submitted.")

func _on_begin_child_pressed():
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		_set_status("Brain not connected.")
		return
	socket.send_text(JSON.stringify({"type": "get_onboarding_script"}))
	if tabs:
		tabs.current_tab = 1
	_set_status("Child session started.")
	_update_warmup_hint()

func _collect_parent_baseline() -> Dictionary:
	return {
		"age": int(age_spin.value),
		"communication_style": {
			"mode": _option_text(comm_mode),
			"processing_latency": _option_text(latency_pref),
			"literalness": _option_text(literalness_pref)
		},
		"sensory_profile": {
			"sound_sensitivity": _option_text(sound_sens),
			"visual_sensitivity": _option_text(visual_sens)
		},
		"regulation_signals": {
			"demand_avoidance": _option_text(demand_pref),
			"recovery_speed": _option_text(recovery_pref)
		},
		"warmup_runs": {
			"enabled": bool(warmup_toggle.button_pressed) if warmup_toggle else false,
			"same_child": true,
			"total_runs": 3
		},
		"autism_traits": float(autism_slider.value),
		"adhd_traits": float(adhd_slider.value),
		"interest_anchors": _parse_interests(interests_field.text),
		"learning_notes": {
			"notes": parent_notes.text
		}
	}

func _option_text(ob: OptionButton) -> String:
	if not ob:
		return "medium"
	return ob.get_item_text(ob.selected).to_lower()

func _parse_interests(raw: String) -> Array:
	var out: Array = []
	for p in raw.split(","):
		var s = p.strip_edges()
		if s != "":
			out.append(s)
	return out

func _show_current_prompt():
	if script_index < 0 or script_index >= script_items.size():
		child_prompt.text = "All done. Click Finish."
		return
	var item = script_items[script_index]
	child_prompt.text = str(item.get("prompt", "Let's play together."))
	prompt_started_ms = Time.get_ticks_msec()
	option_a.text = "I like this"
	option_b.text = "Different one"
	option_c.text = "Skip for now"

func _on_child_option(label: String):
	var latency = float(Time.get_ticks_msec() - prompt_started_ms) / 1000.0
	_send_onboarding_metric("latency_to_choice", latency, {"option": label, "step": script_index})
	_send_onboarding_metric("voluntary_action_count", 1.0, {"step": script_index})
	if label == "C":
		_send_onboarding_metric("partial_attempt_rate", 1.0, {"step": script_index})
	_advance_script()

func _skip_current():
	_send_onboarding_metric("partial_attempt_rate", 1.0, {"step": script_index, "skip": true})
	_advance_script()

func _advance_script():
	script_index += 1
	if script_index >= script_items.size():
		child_prompt.text = "Great work. Click Finish to build your plan."
		return
	_show_current_prompt()

func _finish_onboarding():
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		_set_status("Brain not connected.")
		return
	socket.send_text(JSON.stringify({
		"type": "finish_onboarding",
		"session_id": session_id
	}))
	_set_status("Finalizing onboarding summary...")

func _send_onboarding_metric(metric_key: String, metric_value: float, metadata := {}):
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	socket.send_text(JSON.stringify({
		"type": "onboarding_event",
		"session_id": session_id,
		"event": {
			"metric_key": metric_key,
			"metric_value": metric_value,
			"metadata": metadata
		}
	}))

func _set_child_controls_enabled(enabled: bool):
	option_a.disabled = not enabled
	option_b.disabled = not enabled
	option_c.disabled = not enabled
	next_button.disabled = not enabled
	skip_button.disabled = not enabled
	finish_button.disabled = false

func _set_status(text: String):
	if status_label:
		status_label.text = text

func _set_session_id_for_run():
	var run_idx = int(warmup_info.get("current_run", 1))
	session_id = "run_%d_%d" % [run_idx, Time.get_unix_time_from_system()]

func _update_warmup_hint():
	if not begin_child_button:
		return
	_render_warmup_dots()
	var enabled = bool(warmup_info.get("enabled", false))
	begin_child_button.text = "Begin Child Session"
	if enabled:
		child_hint.text = "Use low-pressure language. This should feel like co-play, not a test."

func _render_warmup_dots():
	if not warmup_track:
		return
	var enabled = bool(warmup_info.get("enabled", false))
	warmup_track.visible = enabled
	if not enabled:
		return
	var completed = int(warmup_info.get("completed_runs", 0))
	var current_run = int(warmup_info.get("current_run", 1))
	var dots = [warmup_dot_1, warmup_dot_2, warmup_dot_3]
	for i in range(3):
		var dot = dots[i]
		if not dot:
			continue
		var run_num = i + 1
		if run_num <= completed:
			dot.color = Color(0.28, 0.55, 0.42, 1.0) # completed
		elif run_num == current_run:
			dot.color = Color(0.35, 0.44, 0.62, 1.0) # current
		else:
			dot.color = Color(0.25, 0.28, 0.31, 1.0) # pending
