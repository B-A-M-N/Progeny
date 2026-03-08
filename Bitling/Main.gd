extends Node2D

var socket = WebSocketPeer.new()
var ws_urls = []
var ws_index = 0
var last_state = WebSocketPeer.STATE_CLOSED
var connecting_seconds = 0.0

var bitling_body: Sprite2D
var status_label: Label
var light: PointLight2D
var overlay_menu: PopupMenu
var chat_panel: Panel
var chat_log: RichTextLabel
var chat_input: LineEdit
var send_button: Button

var is_connected = false
var time_passed = 0.0
var neuro_profile = {}
var trust_model = {}
var world_anchor = {}
var writing_pad_url = ""
var writing_pad_qr_url = ""
var first_contact = {}
var current_action = ""
var action_time = 0.0
var is_dragging = false
var drag_offset = Vector2i.ZERO
var clickthrough_enabled = false

const MENU_TALK := 1
const MENU_REGENERATE := 2
const MENU_PIN_TOGGLE := 3
const MENU_HIDE_CHAT := 4
const MENU_OPEN_PAD := 5
const MENU_SHOW_PAD_URL := 6
const MENU_OPEN_PAD_QR := 7
const MENU_SHOW_PAD_QR_URL := 8
const MENU_QUIT := 9

func _ready():
	_configure_overlay_window()
	bitling_body = get_node_or_null("BitlingBody")
	status_label = get_node_or_null("StatusLabel")
	light = get_node_or_null("PointLight2D")
	overlay_menu = get_node_or_null("OverlayMenu")
	chat_panel = get_node_or_null("ChatPanel")
	chat_log = get_node_or_null("ChatPanel/ChatVBox/ChatLog")
	chat_input = get_node_or_null("ChatPanel/ChatVBox/ChatRow/ChatInput")
	send_button = get_node_or_null("ChatPanel/ChatVBox/ChatRow/SendButton")
	_setup_ui()
	
	# Load the texture from the global Singleton
	if bitling_body and BitlingState.bitling_texture:
		bitling_body.texture = BitlingState.bitling_texture
		print("Bitling body loaded from global state.")
	
	_build_ws_urls()
	_connect_to_brain()

func _setup_ui():
	if overlay_menu:
		overlay_menu.clear()
		overlay_menu.add_item("Talk", MENU_TALK)
		overlay_menu.add_item("Regenerate Avatar", MENU_REGENERATE)
		overlay_menu.add_item("Unpin (Click-through OFF)", MENU_PIN_TOGGLE)
		overlay_menu.add_item("Hide Chat", MENU_HIDE_CHAT)
		overlay_menu.add_item("Open Writing Pad", MENU_OPEN_PAD)
		overlay_menu.add_item("Show Writing URL", MENU_SHOW_PAD_URL)
		overlay_menu.add_item("Open Writing QR", MENU_OPEN_PAD_QR)
		overlay_menu.add_item("Show Writing QR URL", MENU_SHOW_PAD_QR_URL)
		overlay_menu.add_separator()
		overlay_menu.add_item("Quit", MENU_QUIT)
		overlay_menu.id_pressed.connect(_on_menu_id_pressed)
	if chat_input:
		chat_input.text_submitted.connect(_on_chat_submitted)
	if send_button:
		send_button.pressed.connect(func(): _on_chat_submitted(chat_input.text if chat_input else ""))

func _configure_overlay_window():
	var win_id = 0
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true, win_id)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true, win_id)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_TRANSPARENT, true, win_id)
	# Compact, companion-style overlay near bottom-right.
	DisplayServer.window_set_size(Vector2i(480, 520), win_id)
	var screen = DisplayServer.screen_get_usable_rect()
	var x = max(0, screen.position.x + screen.size.x - 520)
	var y = max(0, screen.position.y + screen.size.y - 620)
	DisplayServer.window_set_position(Vector2i(x, y), win_id)
	# Start pinned (interactive). Unpin turns click-through on.
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_MOUSE_PASSTHROUGH, false, win_id)

func _build_ws_urls():
	ws_urls = []
	for ip in IP.get_local_addresses():
		if ip == "" or ip.find(":") != -1 or ip.begins_with("127."):
			continue
		var candidate = "ws://" + ip + ":9001/"
		if not ws_urls.has(candidate):
			ws_urls.append(candidate)
	ws_urls.append("ws://127.0.0.1:9001/")
	ws_urls.append("ws://localhost:9001/")
	print("[Main WS] Candidate URLs: ", ws_urls)

func _connect_to_brain():
	if socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		socket.close()
	socket.supported_protocols = PackedStringArray([])
	var ws_url = ws_urls[ws_index]
	connecting_seconds = 0.0
	print("[Main WS] Connecting to: ", ws_url)
	var err = socket.connect_to_url(ws_url)
	if err != OK:
		print("[Main WS] Connect call failed: ", err)

func _process(delta):
	socket.poll()
	time_passed += delta
	var state = socket.get_ready_state()
	if state == WebSocketPeer.STATE_CONNECTING:
		connecting_seconds += delta
		if connecting_seconds > 2.5:
			print("[Main WS] Connect timeout. Cycling endpoint...")
			socket.close()
	if state != last_state:
		last_state = state
		if state == WebSocketPeer.STATE_OPEN:
			print("[Main WS] OPEN.")
		elif state == WebSocketPeer.STATE_CLOSED:
			ws_index = (ws_index + 1) % ws_urls.size()
			print("[Main WS] CLOSED. Cycling.")
			_connect_to_brain()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not is_connected:
			if status_label:
				status_label.visible = false
			is_connected = true
			
		while socket.get_available_packet_count():
			var packet = socket.get_packet()
			var json_string = packet.get_string_from_utf8()
			handle_message(json_string)
			
	elif state == WebSocketPeer.STATE_CLOSED:
		if status_label:
			status_label.visible = true
			status_label.text = "RECONNECTING..."
			status_label.modulate = Color(1, 0.6, 0.2)
		is_connected = false

	# CORE AUTOMATION: Procedural Animation Engine
	animate_bitling(delta)
	_update_drag()

func _unhandled_input(event):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			_show_context_menu()
			return
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed and _is_mouse_over_avatar():
				is_dragging = true
				drag_offset = DisplayServer.mouse_get_position() - DisplayServer.window_get_position()
			else:
				is_dragging = false

func _update_drag():
	if not is_dragging:
		return
	var mouse_pos = DisplayServer.mouse_get_position()
	DisplayServer.window_set_position(mouse_pos - drag_offset)

func _is_mouse_over_avatar() -> bool:
	if not bitling_body or not bitling_body.texture:
		return false
	var local = bitling_body.to_local(get_viewport().get_mouse_position())
	var size = bitling_body.texture.get_size()
	var half = size * 0.5
	return local.x >= -half.x and local.x <= half.x and local.y >= -half.y and local.y <= half.y

func _show_context_menu():
	if not overlay_menu:
		return
	overlay_menu.set_item_text(overlay_menu.get_item_index(MENU_PIN_TOGGLE), "Pin (Interactive ON)" if clickthrough_enabled else "Unpin (Click-through ON)")
	overlay_menu.position = get_viewport().get_mouse_position()
	overlay_menu.popup()

func _on_menu_id_pressed(id: int):
	match id:
		MENU_TALK:
			if chat_panel:
				chat_panel.visible = true
				if chat_input:
					chat_input.grab_focus()
		MENU_REGENERATE:
			get_tree().change_scene_to_file("res://Creator.tscn")
		MENU_PIN_TOGGLE:
			clickthrough_enabled = not clickthrough_enabled
			DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_MOUSE_PASSTHROUGH, clickthrough_enabled, 0)
		MENU_HIDE_CHAT:
			if chat_panel:
				chat_panel.visible = false
		MENU_OPEN_PAD:
			_open_writing_pad()
		MENU_SHOW_PAD_URL:
			_show_writing_pad_url()
		MENU_OPEN_PAD_QR:
			_open_writing_pad_qr()
		MENU_SHOW_PAD_QR_URL:
			_show_writing_pad_qr_url()
		MENU_QUIT:
			get_tree().quit()

func _on_chat_submitted(text: String):
	var msg = text.strip_edges()
	if msg == "":
		return
	if chat_log:
		chat_log.text += "\n[b]You:[/b] " + msg
	if chat_input:
		chat_input.text = ""
	if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
		socket.send_text(JSON.stringify({"type": "chat_user", "text": msg}))

func handle_message(json_str: String):
	var json = JSON.new()
	if json.parse(json_str) == OK:
		var data = json.data
		var type = data.get("type")
		
		match type:
			"init":
				neuro_profile = data.get("neurodiversity", {})
				trust_model = data.get("trust_model", {})
				world_anchor = data.get("world_anchor", {})
				writing_pad_url = str(data.get("writing_pad_url", ""))
				writing_pad_qr_url = str(data.get("writing_pad_qr_url", ""))
				first_contact = data.get("first_contact", {})
				apply_sensory_settings()
				var name = data.get("profile", {}).get("name", "Bitling")
				var ob = data.get("open_brain", {})
				var ob_ok = bool(ob.get("connected", false))
				var ob_text = "OPEN BRAIN: " + ("CONNECTED" if ob_ok else "DISCONNECTED")
				var greeting = str(data.get("return_greeting", ""))
				var stage = str(trust_model.get("stage", "safety"))
				var location = str(world_anchor.get("location", "world")).replace("_", " ")
				if status_label:
					status_label.text = "HELLO, I AM " + name.to_upper() + " | " + ob_text + " | TRUST: " + stage.to_upper() + " | " + location.to_upper()
				if chat_log and greeting != "":
					chat_log.text += "\n[b]Bitling:[/b] " + greeting
				if chat_log and bool(first_contact.get("active", false)):
					chat_log.text += "\n[i]First Contact:[/i] Mystery/play mode is active (short session)."
				if chat_log and writing_pad_url != "":
					chat_log.text += "\n[i]Writing pad:[/i] " + writing_pad_url
				if chat_log and writing_pad_qr_url != "":
					chat_log.text += "\n[i]Writing QR:[/i] " + writing_pad_qr_url
				print("[OpenBrain] ", ob_text, " detail=", str(ob.get("detail", "")))
				
			"speak":
				if status_label: status_label.text = data.get("text", "").to_upper()
				trigger_action("speaking", 2.0)
				
			"action":
				var action = data.get("action")
				trigger_action(action, 1.5)
				
			"state_change":
				var state = data.get("state")
				if state == "RESEARCHING":
					trigger_action("thinking", 3.0)
			"lesson_plan":
				var subject = str(data.get("subject", "topic"))
				var lesson = data.get("lesson", {})
				var hook = str(lesson.get("hook", "Let's learn together."))
				var facts = lesson.get("facts", [])
				var activity = str(lesson.get("activity", "Let's try one tiny step."))
				var mode = str(lesson.get("mode", "stabilize"))
				if status_label:
					status_label.text = ("LESSON: " + subject + " | " + hook + " | MODE: " + mode).to_upper()
				if chat_log:
					var msg = "\n[b]Bitling Lesson (" + subject + "):[/b] " + hook
					if typeof(facts) == TYPE_ARRAY and facts.size() > 0:
						msg += "\n- " + str(facts[0])
						if facts.size() > 1:
							msg += "\n- " + str(facts[1])
						if facts.size() > 2:
							msg += "\n- " + str(facts[2])
					msg += "\n[b]Activity:[/b] " + activity
					msg += "\n[b]Mode:[/b] " + mode
					chat_log.text += msg
			"adaptive_state":
				var st = data.get("state", {})
				var stage = str(st.get("trust_stage", trust_model.get("stage", "safety")))
				var mode = str(data.get("policy", {}).get("mode", "stabilize"))
				if status_label:
					status_label.text = ("MODE: " + mode + " | TRUST: " + stage).to_upper()
			"world_state":
				world_anchor = data.get("world_anchor", world_anchor)
				trust_model = data.get("trust_model", trust_model)
				first_contact = data.get("first_contact", first_contact)
				var pad_url = str(data.get("writing_pad_url", ""))
				var pad_qr_url = str(data.get("writing_pad_qr_url", ""))
				if pad_url != "":
					writing_pad_url = pad_url
				if pad_qr_url != "":
					writing_pad_qr_url = pad_qr_url
				var line = _world_status_line()
				if status_label:
					status_label.text = line.to_upper()
				if chat_log:
					var g = str(data.get("return_greeting", ""))
					if g != "":
						chat_log.text += "\n[b]Bitling:[/b] " + g
			"trust_stage_update":
				trust_model = data.get("trust_model", trust_model)
				if chat_log:
					var stage2 = str(trust_model.get("stage", "safety"))
					chat_log.text += "\n[i]Trust grew to:[/i] " + stage2
			"writing_pad_info":
				writing_pad_url = str(data.get("url", writing_pad_url))
				writing_pad_qr_url = str(data.get("qr_url", writing_pad_qr_url))
				_show_writing_pad_url()
			"first_contact_completed":
				var msg_fc = str(data.get("message", "Tomorrow we open a tiny portal together."))
				if chat_log:
					chat_log.text += "\n[b]Bitling:[/b] " + msg_fc
				if status_label:
					status_label.text = "FIRST CONTACT COMPLETE"

func trigger_action(action_name: String, duration: float):
	current_action = action_name
	action_time = duration
	print("Automated Action Triggered: ", action_name)

func animate_bitling(delta):
	if not bitling_body: return
	
	# 1. BASE "BREATHING" (Always active)
	var breathe_speed = 2.3
	var breathe_amount = 0.05
	var squash = sin(time_passed * breathe_speed) * breathe_amount
	bitling_body.scale = Vector2(0.82 - squash * 0.4, 0.82 + squash)
	
	# 2. DEFAULT "BOBBY" MOVEMENT
	var float_range = 14.0
	bitling_body.position.y = 330 + sin(time_passed * 3.0) * float_range
	bitling_body.position.x = 240 + sin(time_passed * 1.7) * 4.0
	bitling_body.rotation = sin(time_passed * 1.4) * 0.03

	# 3. ACTION-SPECIFIC OVERRIDES (Automated Reactions)
	if action_time > 0:
		action_time -= delta
		match current_action:
			"praise_attempt", "celebrate":
				bitling_body.rotation = sin(time_passed * 20.0) * 0.1
				bitling_body.position.y -= 50 # Jump up
			"speaking":
				var talk_pulse = abs(sin(time_passed * 15.0)) * 0.08
				bitling_body.scale += Vector2(talk_pulse, talk_pulse)
				bitling_body.rotation = sin(time_passed * 6.5) * 0.05
			"thinking", "retrieve_content":
				bitling_body.rotation = sin(time_passed * 1.5) * 0.12
				if light: light.energy = 2.0 + sin(time_passed * 4.0)
			"visual_stim":
				if light: 
					light.energy = 3.0
					light.color = Color(0, 1, 1) # Cyan pulse
			"suggest_break":
				bitling_body.skew = sin(time_passed * 2.0) * 0.05
	else:
		# Reset to calm state
		bitling_body.rotation = lerp(bitling_body.rotation, 0.0, 0.1)
		bitling_body.skew = lerp(bitling_body.skew, 0.0, 0.1)
		if light: light.energy = lerp(light.energy, 1.5, 0.1)

func apply_sensory_settings():
	var sensory = neuro_profile.get("sensory", {})
	var visual_sens = sensory.get("visual_sensitivity", "medium")
	var vibe = sensory.get("preferred_visual_vibe", "calm")
	
	var modulate = get_node_or_null("CanvasModulate")
	
	if modulate:
		if visual_sens == "high": # Avoidant - make it dimmer
			modulate.color = Color(0.3, 0.3, 0.3, 1.0)
		elif visual_sens == "low": # Seeking - make it brighter
			modulate.color = Color(0.8, 0.8, 0.8, 1.0)
		else:
			modulate.color = Color(0.6, 0.6, 0.6, 1.0)
			
	if light:
		if vibe == "calm":
			light.color = Color(0.4, 0.6, 1.0, 1.0) # Soft blue
			light.energy = 1.0
		else:
			light.color = Color(1.0, 0.8, 0.4, 1.0) # Warm energetic
			light.energy = 2.0
	
	print("Sensory settings applied: ", visual_sens, " | ", vibe)

func _world_status_line() -> String:
	var stage = str(trust_model.get("stage", "safety"))
	var world_name = str(world_anchor.get("location", "world")).replace("_", " ")
	var companions = world_anchor.get("companions", [])
	var c = ""
	if typeof(companions) == TYPE_ARRAY and companions.size() > 0:
		c = " | companions: " + ", ".join(companions)
	return "Trust: " + stage + " | world: " + world_name + c

func _open_writing_pad():
	if writing_pad_url == "":
		if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
			socket.send_text(JSON.stringify({"type": "get_writing_pad_url"}))
		if status_label:
			status_label.text = "REQUESTING WRITING PAD URL..."
		return
	OS.shell_open(writing_pad_url)
	if status_label:
		status_label.text = ("OPENED WRITING PAD: " + writing_pad_url).to_upper()

func _show_writing_pad_url():
	if writing_pad_url == "":
		if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
			socket.send_text(JSON.stringify({"type": "get_writing_pad_url"}))
		if status_label:
			status_label.text = "WRITING PAD URL UNAVAILABLE"
		return
	if chat_log:
		chat_log.text += "\n[i]Tablet/Kindle URL:[/i] " + writing_pad_url
	if status_label:
		status_label.text = ("WRITING PAD: " + writing_pad_url).to_upper()

func _open_writing_pad_qr():
	if writing_pad_qr_url == "":
		if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
			socket.send_text(JSON.stringify({"type": "get_writing_pad_url"}))
		if status_label:
			status_label.text = "REQUESTING WRITING PAD QR..."
		return
	OS.shell_open(writing_pad_qr_url)
	if status_label:
		status_label.text = ("OPENED WRITING QR: " + writing_pad_qr_url).to_upper()

func _show_writing_pad_qr_url():
	if writing_pad_qr_url == "":
		if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
			socket.send_text(JSON.stringify({"type": "get_writing_pad_url"}))
		if status_label:
			status_label.text = "WRITING PAD QR URL UNAVAILABLE"
		return
	if chat_log:
		chat_log.text += "\n[i]Writing QR URL:[/i] " + writing_pad_qr_url
	if status_label:
		status_label.text = ("WRITING QR: " + writing_pad_qr_url).to_upper()

func trigger_visual_stim():
	var tween = create_tween()
	var light_node = get_node_or_null("PointLight2D")
	if light_node:
		tween.tween_property(light_node, "energy", 3.0, 1.0)
		tween.tween_property(light_node, "energy", 1.5, 1.0)
	print("Visual Stim triggered for co-regulation.")
