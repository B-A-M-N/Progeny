extends Control
class_name Creator

# Global static variable to pass texture between scenes
static var bitling_texture: Texture2D

var socket = WebSocketPeer.new()
var ws_urls = []
var ws_index = 0
var connecting_seconds = 0.0

var last_state = WebSocketPeer.STATE_CLOSED

# Direct Path References (Workbench Edition)
@onready var input_field = $Workbench/ControlSection/InputField
@onready var style_button = $Workbench/ControlSection/StyleButton
@onready var model_button = $Workbench/ControlSection/EngineSettings/ModelButton
@onready var enhance_toggle = $Workbench/ControlSection/EngineSettings/EnhanceToggle
@onready var seed_toggle = $Workbench/ControlSection/EngineSettings/SeedToggle
@onready var lora_field = $Workbench/ControlSection/LoraField
@onready var lora_search_field = $Workbench/ControlSection/LoraBrowseRow/LoraSearchField
@onready var lora_browse_button = $Workbench/ControlSection/LoraBrowseRow/LoraBrowseButton
@onready var lora_results = $Workbench/ControlSection/LoraResults
@onready var demo_label = $Workbench/ControlSection/DemoLabel
@onready var create_button = $Workbench/ControlSection/ActionButtons/CreateButton
@onready var regen_button = $Workbench/ControlSection/ActionButtons/HBox/RegenerateButton
@onready var tweak_button = $Workbench/ControlSection/ActionButtons/HBox/TweakButton
@onready var preview_rect = $Workbench/PreviewSection/PreviewArea/PreviewRect
@onready var particles = $Workbench/PreviewSection/PreviewArea/CPUParticles2D
@onready var preview_frame = $Workbench/PreviewSection/PreviewArea/PreviewFrame
@onready var tweak_field = $Workbench/ControlSection/TweakField

var prefer_local = false
var current_texture: Texture2D
var request_timer = 0.0
var is_generating = false
var locked_seed = ""
var lora_result_items: Array = []
var pending_remote_request: Dictionary = {}

func _ready():
	print("--- Creator Workbench (Remote Generator) ---")
	_build_ws_urls()
	
	if input_field:
		input_field.grab_focus()
		input_field.text_submitted.connect(func(_t): _on_create_button_pressed())
	if tweak_field:
		tweak_field.text_submitted.connect(func(_t): _on_tweak_button_pressed())
	if lora_browse_button:
		lora_browse_button.pressed.connect(_on_lora_browse_pressed)
	if lora_search_field:
		lora_search_field.text_submitted.connect(func(_t): _on_lora_browse_pressed())
	if lora_results:
		lora_results.item_selected.connect(_on_lora_result_selected)

	setup_visuals()
	start_brief_demo()
	
	# Wait 1s for engine network to stabilize
	await get_tree().create_timer(1.0).timeout
	_connect_to_brain()

func _build_ws_urls():
	ws_urls = []
	# Prefer LAN IPv4 addresses first; some Godot/sandbox setups can't reach loopback host services.
	for ip in IP.get_local_addresses():
		if ip == "":
			continue
		# Only use IPv4 host literals here; IPv6 requires brackets and was causing bad URLs.
		if ip.find(":") != -1:
			continue
		if ip.begins_with("127."):
			continue
		var candidate = "ws://" + ip + ":9001/"
		if not ws_urls.has(candidate):
			ws_urls.append(candidate)
	# Then fallback to loopback.
	ws_urls.append("ws://127.0.0.1:9001/")
	ws_urls.append("ws://localhost:9001/")
	print("[WebSocket] Candidate URLs: ", ws_urls)

func _connect_to_brain():
	if socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		socket.close()
	
	# Godot 4.3 Handshake Fix: Explicitly set empty protocols
	socket.supported_protocols = PackedStringArray([])
	
	var ws_url = ws_urls[ws_index]
	connecting_seconds = 0.0
	print("[WebSocket] Connecting to: ", ws_url)
	var err = socket.connect_to_url(ws_url)
	if err != OK:
		print("[WebSocket] Connect call failed: ", err)

func _process(delta):
	socket.poll()
	var state = socket.get_ready_state()
	if state == WebSocketPeer.STATE_CONNECTING:
		connecting_seconds += delta
		if connecting_seconds > 2.5:
			print("[WebSocket] Connect timeout. Cycling endpoint...")
			socket.close()
	
	if state != last_state:
		_on_state_changed(last_state, state)
		last_state = state

	if state == WebSocketPeer.STATE_OPEN:
		if pending_remote_request.size() > 0:
			_send_pending_remote_request()
		while socket.get_available_packet_count():
			var packet = socket.get_packet()
			var json_str = packet.get_string_from_utf8()
			handle_backend_message(json_str)
	
	if is_generating:
		request_timer += delta
		var dots = ""
		for i in range(int(request_timer * 2.0) % 4):
			dots += "."
		demo_label.text = "Building myself from the stars" + dots + " (" + str(int(request_timer)) + "s)"
		
		if request_timer > 120.0:
			stop_generation("Generation timed out waiting for backend response.")

func _on_state_changed(_old_state, new_state):
	match new_state:
		WebSocketPeer.STATE_CONNECTING:
			print("[WebSocket] State: CONNECTING...")
		WebSocketPeer.STATE_OPEN:
			print("[WebSocket] State: OPEN! Handshake complete.")
			connecting_seconds = 0.0
			if demo_label.text.contains("not connected"):
				demo_label.text = "Connected! I am ready to be built."
		WebSocketPeer.STATE_CLOSING:
			print("[WebSocket] State: CLOSING...")
		WebSocketPeer.STATE_CLOSED:
			var code = socket.get_close_code()
			var reason = socket.get_close_reason()
			print("[WebSocket] State: CLOSED. Code: %d, Reason: %s" % [code, reason])
			ws_index = (ws_index + 1) % ws_urls.size()
			# Auto-retry after 3 seconds if we aren't connected
			await get_tree().create_timer(3.0).timeout
			if socket.get_ready_state() == WebSocketPeer.STATE_CLOSED:
				_connect_to_brain()

func setup_visuals():
	if preview_frame:
		var stylebox = StyleBoxFlat.new()
		stylebox.bg_color = Color(1, 1, 1, 0.05)
		stylebox.border_width_left = 3
		stylebox.border_width_top = 3
		stylebox.border_width_right = 3
		stylebox.border_width_bottom = 3
		stylebox.border_color = Color(0.4, 0.8, 1, 0.4)
		stylebox.corner_radius_top_left = 30
		stylebox.corner_radius_top_right = 30
		stylebox.corner_radius_bottom_left = 30
		stylebox.corner_radius_bottom_right = 30
		preview_frame.add_theme_stylebox_override("panel", stylebox)

func start_brief_demo():
	if demo_label:
		demo_label.text = "Hello! I am Bitling. Tell me... what should I look like?"

func handle_backend_message(json_str: String):
	var json = JSON.new()
	if json.parse(json_str) == OK:
		var data = json.data
		match data.get("type"):
			"init":
				prefer_local = data.get("generation", {}).get("prefer_local", false)
				print("[Creation] Init received. Prefer Local: ", prefer_local)
				var ob = data.get("open_brain", {})
				var ob_ok = bool(ob.get("connected", false))
				var ob_detail = str(ob.get("detail", "unknown"))
				if demo_label and not is_generating:
					demo_label.text = "Open Brain: " + ("CONNECTED" if ob_ok else "DISCONNECTED")
					if not ob_ok:
						demo_label.text += " (" + ob_detail + ")"
			"tutor_constructed":
				is_generating = false
				if data.get("fallback", false) and demo_label:
					demo_label.text = data.get("message", "Using fallback avatar.")
				load_preview_from_path(data.get("image_url"))
			"error":
				is_generating = false
				stop_generation(data.get("message", "Generation failed."))
			"remote_loras":
				_populate_lora_results(data.get("items", []))

func _on_create_button_pressed():
	if create_button and create_button.text == "Yes! Let's Go!":
		finalize_and_start()
	else:
		start_generation()

func _on_tweak_button_pressed():
	start_tweak()

func _on_regenerate_button_pressed():
	start_generation()

func start_generation():
	if not input_field or input_field.text == "": return
	
	toggle_loading(true)
	is_generating = true
	request_timer = 0.0
	var description = input_field.text
	var style_idx = style_button.selected
	var style_text = style_button.get_item_text(style_idx)
	
	if prefer_local:
		if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
			demo_label.text = "Connecting to brain..."
			_queue_remote_generate(description, style_text)
			return
		socket.send_text(JSON.stringify({
			"type": "construct_tutor_local",
			"description": description,
			"style": style_idx
		}))
	else:
		request_remote_generation(description, style_text)

func _get_seed_value() -> String:
	if seed_toggle and seed_toggle.button_pressed:
		if locked_seed == "":
			locked_seed = str(randi())
		return locked_seed
	locked_seed = ""
	return ""

func _parse_loras() -> Array:
	var parsed: Array = []
	if not lora_field:
		return parsed
	var txt = lora_field.text.strip_edges()
	if txt == "":
		return parsed
	for raw_item in txt.split(","):
		var item = raw_item.strip_edges()
		if item == "":
			continue
		var parts = item.split(":")
		var name_or_id = parts[0].strip_edges()
		var name = name_or_id
		var lora_id = ""
		if name_or_id.contains("|"):
			var id_parts = name_or_id.split("|")
			name = id_parts[0].strip_edges()
			if id_parts.size() > 1:
				lora_id = id_parts[1].strip_edges()
		if name == "":
			continue
		var weight = 0.8
		if parts.size() > 1:
			var wtxt = parts[1].strip_edges()
			if wtxt.is_valid_float():
				weight = clamp(float(wtxt), 0.0, 2.0)
		var payload = {
			"name": name,
			"model": weight,
			"clip": 1.0
		}
		if lora_id != "":
			payload["id"] = lora_id
		parsed.append(payload)
	return parsed

func _on_lora_browse_pressed():
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		if demo_label:
			demo_label.text = "Connecting to brain for LoRA catalog..."
		if socket.get_ready_state() == WebSocketPeer.STATE_CLOSED:
			_connect_to_brain()
		return
	var query = ""
	if lora_search_field:
		query = lora_search_field.text.strip_edges()
	if demo_label:
		demo_label.text = "Loading LoRA catalog..."
	socket.send_text(JSON.stringify({
		"type": "list_remote_loras",
		"query": query,
		"limit": 30
	}))

func _populate_lora_results(items: Array):
	lora_result_items = []
	if not lora_results:
		return
	lora_results.clear()
	for item in items:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var name = str(item.get("name", "")).strip_edges()
		if name == "":
			continue
		var version = str(item.get("version", "")).strip_edges()
		var display = name
		if version != "":
			display += " (" + version + ")"
		lora_results.add_item(display)
		lora_result_items.append(item)
	if demo_label:
		demo_label.text = "LoRA catalog loaded. Click one to add."

func _on_lora_result_selected(index: int):
	if index < 0 or index >= lora_result_items.size():
		return
	var item = lora_result_items[index]
	var name = str(item.get("name", "")).strip_edges()
	if name == "":
		return
	var version_id = str(item.get("version_id", "")).strip_edges()
	if version_id == "":
		version_id = str(item.get("id", "")).strip_edges()
	var insert = name + ":0.8"
	if version_id != "":
		insert = name + "|" + version_id + ":0.8"
	if lora_field:
		var existing = lora_field.text.strip_edges()
		if existing == "":
			lora_field.text = insert
		else:
			lora_field.text = existing + ", " + insert
	var triggers = item.get("trigger_words", [])
	var trigger_text = ""
	if typeof(triggers) == TYPE_ARRAY and triggers.size() > 0:
		trigger_text = " Triggers: " + ", ".join(triggers)
	if demo_label:
		demo_label.text = "Added " + name + "." + trigger_text

func request_remote_generation(description: String, style: String):
	var model = "turbo"
	if model_button:
		var model_text = model_button.get_item_text(model_button.selected).to_lower()
		if model_text.contains("flux"):
			model = "flux"
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		_queue_remote_generate(description, style)
		if demo_label:
			demo_label.text = "Connecting to brain..."
		return
	socket.send_text(JSON.stringify({
		"type": "construct_tutor_remote",
		"description": description,
		"style": style,
		"model": model,
		"enhance_prompt": enhance_toggle and enhance_toggle.button_pressed,
		"seed": _get_seed_value(),
		"loras": _parse_loras()
	}))

func start_tweak():
	if not tweak_field or tweak_field.text == "": return
	toggle_loading(true)
	is_generating = true
	request_timer = 0.0
	
	if prefer_local:
		if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
			demo_label.text = "Connecting to brain..."
			_queue_remote_tweak(input_field.text, tweak_field.text, style_button.get_item_text(style_button.selected))
			return
		socket.send_text(JSON.stringify({
			"type": "tweak_tutor_local",
			"base_image": "assets/generated/tutor_preview.png",
			"tweak_description": tweak_field.text,
			"strength": 0.4
		}))
	else:
		request_remote_tweak(input_field.text, tweak_field.text, style_button.get_item_text(style_button.selected))

func request_remote_tweak(description: String, tweak_description: String, style: String):
	var model = "turbo"
	if model_button:
		var model_text = model_button.get_item_text(model_button.selected).to_lower()
		if model_text.contains("flux"):
			model = "flux"
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		_queue_remote_tweak(description, tweak_description, style)
		if demo_label:
			demo_label.text = "Connecting to brain..."
		return
	socket.send_text(JSON.stringify({
		"type": "tweak_tutor_remote",
		"description": description,
		"tweak_description": tweak_description,
		"style": style,
		"model": model,
		"enhance_prompt": enhance_toggle and enhance_toggle.button_pressed,
		"seed": _get_seed_value(),
		"loras": _parse_loras()
	}))

func _queue_remote_generate(description: String, style: String):
	pending_remote_request = {
		"type": "construct",
		"description": description,
		"style": style
	}
	if socket.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		_connect_to_brain()

func _queue_remote_tweak(description: String, tweak_description: String, style: String):
	pending_remote_request = {
		"type": "tweak",
		"description": description,
		"tweak_description": tweak_description,
		"style": style
	}
	if socket.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		_connect_to_brain()

func _send_pending_remote_request():
	if pending_remote_request.size() == 0:
		return
	var req = pending_remote_request.duplicate()
	pending_remote_request = {}
	var typ = str(req.get("type", ""))
	if typ == "construct":
		request_remote_generation(
			str(req.get("description", "")),
			str(req.get("style", "3D Animated Movie"))
		)
	elif typ == "tweak":
		request_remote_tweak(
			str(req.get("description", "")),
			str(req.get("tweak_description", "")),
			str(req.get("style", "3D Animated Movie"))
		)

func show_preview():
	if preview_rect: preview_rect.texture = current_texture
	toggle_loading(false)
	if create_button: 
		create_button.text = "Yes! Let's Go!"
		create_button.disabled = false
	if tweak_button: tweak_button.visible = true
	if regen_button: regen_button.visible = true
	if tweak_field: 
		tweak_field.visible = true
		tweak_field.grab_focus()
	if demo_label: demo_label.text = "I like this look! Or should I change a small detail?"

func toggle_loading(is_loading: bool):
	if particles: particles.emitting = is_loading
	if create_button: create_button.disabled = is_loading
	if tweak_button: tweak_button.disabled = is_loading
	if regen_button: regen_button.disabled = is_loading

func load_preview_from_path(path: String):
	if path == "":
		return
	var candidate_paths = PackedStringArray([
		path,
		"res://" + path,
		ProjectSettings.globalize_path("res://" + path),
	])
	for p in candidate_paths:
		var image = Image.load_from_file(p)
		if image:
			current_texture = ImageTexture.create_from_image(image)
			show_preview()
			return
	stop_generation("Generated image could not be loaded from: " + path)

func finalize_and_start():
	BitlingState.bitling_texture = current_texture
	if socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
		socket.send_text(JSON.stringify({"type": "finalize_tutor"}))
	else:
		print("[Creation] Finalize skipped: brain not connected.")
	get_tree().change_scene_to_file("res://Onboarding.tscn")

func stop_generation(msg):
	if demo_label: demo_label.text = msg
	toggle_loading(false)
