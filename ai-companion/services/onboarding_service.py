import time
from copy import deepcopy


class OnboardingService:
    def __init__(self, memory_service, config):
        self.memory = memory_service
        self.config = config or {}

    def get_session_script(self):
        return [
            {"id": "companion_choice", "prompt": "Every explorer needs a helper friend. Which one should join us?", "type": "choice", "skip_allowed": True},
            {"id": "draw_interest", "prompt": "Can you show me something you really like?", "type": "drawing", "skip_allowed": True},
            {"id": "show_faces", "prompt": "Can you show me a happy, tired, and silly face?", "type": "camera_play", "skip_allowed": True},
            {"id": "fast_slow", "prompt": "Can you show me FAST drawing and then SLOW drawing?", "type": "drawing_pace", "skip_allowed": True},
            {"id": "interest_fork", "prompt": "Dinosaurs or rockets? Ocean or space? Drawing or building?", "type": "choice", "skip_allowed": True},
            {"id": "mini_challenge", "prompt": "Want to try something tiny together?", "type": "micro_task", "skip_allowed": True},
            {"id": "recovery", "prompt": "Can you draw one big circle?", "type": "easy_success", "skip_allowed": True},
        ]

    def get_or_init_profile(self):
        existing = self.memory.get_adaptation_profile()
        if existing:
            return existing
        profile = self._default_profile()
        self.memory.upsert_adaptation_profile(profile, source="default_init")
        return profile

    def apply_parent_baseline(self, baseline):
        base = self.get_or_init_profile()
        out = deepcopy(base)
        b = baseline or {}

        def _norm3(v, default=0.5):
            if isinstance(v, (int, float)):
                return max(0.0, min(1.0, float(v)))
            s = str(v or "").strip().lower()
            mapping = {"low": 0.2, "medium": 0.5, "high": 0.8, "very_high": 0.95, "very_low": 0.05}
            return mapping.get(s, default)

        traits = out["traits"]
        sensory = b.get("sensory_profile", {})
        comm = b.get("communication_style", {})
        regulation = b.get("regulation_signals", {})

        traits["sensory_audio"] = _norm3(sensory.get("sound_sensitivity"), traits["sensory_audio"])
        traits["sensory_visual"] = _norm3(sensory.get("visual_sensitivity"), traits["sensory_visual"])
        traits["processing_latency"] = _norm3(comm.get("processing_latency"), traits["processing_latency"])
        traits["literalness"] = _norm3(comm.get("literalness"), traits["literalness"])
        traits["demand_avoidance"] = _norm3(regulation.get("demand_avoidance"), traits["demand_avoidance"])
        traits["frustration_recovery"] = _norm3(regulation.get("recovery_speed"), traits["frustration_recovery"])
        traits["autism_traits"] = _norm3(b.get("autism_traits"), traits["autism_traits"])
        traits["adhd_traits"] = _norm3(b.get("adhd_traits"), traits["adhd_traits"])

        anchors = b.get("interest_anchors", [])
        if isinstance(anchors, list):
            out["interest_anchors"] = [str(x).strip() for x in anchors if str(x).strip()][:20]

        out["parent_notes"] = b.get("learning_notes", {})
        out["updated_at"] = time.time()
        out["source"] = "parent_baseline"
        out["policy"] = self._derive_policy(traits)
        out["neurodiversity_profile"] = self._to_neurodiversity_profile(out)
        self.memory.upsert_adaptation_profile(out, source="parent_baseline")
        return out

    def apply_runtime_metrics(self, metrics):
        current = self.get_or_init_profile()
        out = deepcopy(current)
        m = metrics or {}
        traits = out["traits"]

        # Smooth updates prevent overreaction to one moment.
        def blend(old, new, alpha=0.2):
            return max(0.0, min(1.0, (1.0 - alpha) * float(old) + alpha * float(new)))

        if "latency_to_start" in m:
            # Longer latency implies higher processing demand.
            est = min(1.0, max(0.0, float(m["latency_to_start"]) / 12.0))
            traits["processing_latency"] = blend(traits["processing_latency"], est)
        if "pressure_variance" in m:
            est = min(1.0, max(0.0, float(m["pressure_variance"])))
            traits["motor_variability"] = blend(traits["motor_variability"], est)
        if "recovery_time" in m:
            est = 1.0 - min(1.0, max(0.0, float(m["recovery_time"]) / 15.0))
            traits["frustration_recovery"] = blend(traits["frustration_recovery"], est)
        if "lookaway_frequency" in m:
            est = min(1.0, max(0.0, float(m["lookaway_frequency"])))
            traits["attention_shift_rate"] = blend(traits["attention_shift_rate"], est)

        out["updated_at"] = time.time()
        out["source"] = "runtime_metrics"
        out["policy"] = self._derive_policy(traits)
        out["neurodiversity_profile"] = self._to_neurodiversity_profile(out)
        self.memory.upsert_adaptation_profile(out, source="runtime_metrics")
        return out

    def summarize_for_parent(self, session_metrics):
        m = session_metrics or {}
        strengths = []
        friction = []
        if float(m.get("engagement_duration", 0)) >= 300:
            strengths.append("High sustained engagement during play moments.")
        if float(m.get("retry_success_rate", 0)) >= 0.5:
            strengths.append("Good persistence after initial mistakes.")
        if float(m.get("pressure_spike_frequency", 0)) > 0.3:
            friction.append("Pressure spikes suggest frustration during harder motor tasks.")
        if float(m.get("latency_to_start", 0)) > 8:
            friction.append("Long start latency suggests processing delay before unfamiliar prompts.")
        if not strengths:
            strengths.append("Responded to low-pressure, co-play language.")
        if not friction:
            friction.append("No major friction spikes observed in this session.")

        plan = self._starter_plan()
        return {
            "strengths": strengths,
            "friction_points": friction,
            "suggested_pacing": "short_visual_tasks_with_choice",
            "starter_plan_7d": plan
        }

    def estimate_live_state(self, state_summary, recent_signals=None):
        s = state_summary or {}
        sig = recent_signals or {}
        engagement_raw = str(s.get("engagement_level", "none")).lower()
        if engagement_raw == "high":
            engagement = "high"
        elif engagement_raw == "medium":
            engagement = "steady"
        elif engagement_raw == "low":
            engagement = "drifting"
        else:
            engagement = "disengaged"

        struggle_count = len(s.get("struggles_detected", []) or [])
        pressure_spikes = float(sig.get("pressure_spike_frequency", 0.0))
        pause_count = float(sig.get("micro_pause_count", 0.0))
        abandonment = float(sig.get("partial_attempt_rate", 0.0))

        frustration = "none"
        if struggle_count > 0 or pressure_spikes > 0.15:
            frustration = "mild"
        if struggle_count > 1 or pressure_spikes > 0.30 or abandonment > 0.2:
            frustration = "moderate"
        if struggle_count > 2 or pressure_spikes > 0.45:
            frustration = "acute"

        cognitive_load = "workable"
        if pause_count > 6 or abandonment > 0.15:
            cognitive_load = "elevated"
        if pause_count > 12 or abandonment > 0.30:
            cognitive_load = "high"

        regulation = "regulated"
        if frustration in ("mild", "moderate"):
            regulation = "wobbling"
        if frustration == "acute":
            regulation = "dysregulated"

        confidence = "secure"
        if frustration in ("mild", "moderate"):
            confidence = "cautious"
        if frustration in ("moderate", "acute"):
            confidence = "fragile"
        if engagement == "disengaged":
            confidence = "avoidant"

        readiness = "hold_steady"
        if engagement in ("high", "steady") and frustration in ("none", "mild") and cognitive_load in ("workable", "low"):
            readiness = "can_increase"
        if frustration in ("moderate", "acute"):
            readiness = "reduce_demand"
        if regulation == "dysregulated":
            readiness = "switch_modality"

        escalation = self.compute_escalation_profile(s, sig)
        phase = self._infer_phase(engagement, cognitive_load, frustration, regulation, readiness, escalation, sig)

        return {
            "engagement": engagement,
            "cognitive_load": cognitive_load,
            "frustration": frustration,
            "regulation": regulation,
            "confidence": confidence,
            "challenge_readiness": readiness,
            "escalation_score": escalation["score"],
            "escalation_band": escalation["band"],
            "escalation_signals": escalation["signals"],
            "phase": phase,
        }

    def select_mode(self, live_state):
        st = live_state or {}
        phase = str(st.get("phase", ""))
        if phase in ("recover", "rest", "co_play", "explore", "engage", "practice"):
            return phase
        if st.get("regulation") == "dysregulated" or st.get("challenge_readiness") == "switch_modality":
            return "recover"
        if st.get("frustration") in ("moderate", "acute"):
            return "repair"
        if st.get("cognitive_load") == "elevated" or st.get("challenge_readiness") == "hold_steady":
            return "stabilize"
        return "advance"

    def render_adaptive_policy(self, live_state):
        mode = self.select_mode(live_state)
        if mode == "rest":
            return {
                "mode": mode,
                "prompt_style": "quiet_story",
                "prompt_length": "very_short",
                "sensory_density": "very_low",
                "task_granularity": "none",
                "modality": "passive_or_choice",
            }
        if mode == "co_play":
            return {
                "mode": mode,
                "prompt_style": "co_play",
                "prompt_length": "short",
                "sensory_density": "low",
                "task_granularity": "micro",
                "modality": "play",
            }
        if mode == "explore":
            return {
                "mode": mode,
                "prompt_style": "choice_or_story",
                "prompt_length": "short",
                "sensory_density": "moderate",
                "task_granularity": "open",
                "modality": "discovery",
            }
        if mode == "engage":
            return {
                "mode": mode,
                "prompt_style": "interactive",
                "prompt_length": "short",
                "sensory_density": "moderate",
                "task_granularity": "small_steps",
                "modality": "interactive",
            }
        if mode == "practice":
            return {
                "mode": mode,
                "prompt_style": "repetition_game",
                "prompt_length": "short",
                "sensory_density": "moderate",
                "task_granularity": "repeatable",
                "modality": "guided_practice",
            }
        if mode == "recover":
            return {
                "mode": mode,
                "prompt_style": "co_play",
                "prompt_length": "very_short",
                "sensory_density": "low",
                "task_granularity": "micro",
                "modality": "drawing_or_choice",
            }
        if mode == "repair":
            return {
                "mode": mode,
                "prompt_style": "declarative",
                "prompt_length": "short",
                "sensory_density": "low",
                "task_granularity": "small_steps",
                "modality": "co_play",
            }
        if mode == "stabilize":
            return {
                "mode": mode,
                "prompt_style": "co_play",
                "prompt_length": "short",
                "sensory_density": "moderate",
                "task_granularity": "small_steps",
                "modality": "current",
            }
        return {
            "mode": mode,
            "prompt_style": "choice_or_direct",
            "prompt_length": "normal",
            "sensory_density": "moderate",
            "task_granularity": "progressive",
            "modality": "challenge",
        }

    def compute_escalation_profile(self, state_summary, recent_signals=None):
        s = state_summary or {}
        sig = recent_signals or {}

        # 12 early escalation channels (normalized 0..1)
        channels = {
            "response_latency_spike": self._clamp(sig.get("response_latency_spike", sig.get("latency_to_choice", 0.0))),
            "rapid_topic_switching": self._clamp(sig.get("rapid_topic_switching", sig.get("topic_switch_rate", 0.0))),
            "vocal_intensity": self._clamp(sig.get("vocal_intensity", 0.0)),
            "repetitive_language_looping": self._clamp(sig.get("repetitive_language_looping", 0.0)),
            "movement_acceleration": self._clamp(sig.get("movement_acceleration", 0.0)),
            "micro_frustration": self._clamp(max(sig.get("micro_frustration", 0.0), sig.get("pressure_spike_frequency", 0.0))),
            "interruptions": self._clamp(sig.get("interruptions", sig.get("interruption_rate", 0.0))),
            "humor_deflection": self._clamp(sig.get("humor_deflection", 0.0)),
            "silence_withdrawal": self._clamp(sig.get("silence_withdrawal", 0.0)),
            "task_abandonment": self._clamp(max(sig.get("task_abandonment", 0.0), sig.get("partial_attempt_rate", 0.0))),
            "facial_regulation_changes": self._clamp(sig.get("facial_regulation_changes", sig.get("facial_tension", 0.0))),
            "breathing_pattern_shift": self._clamp(sig.get("breathing_pattern_shift", sig.get("breathing_shift", 0.0))),
        }

        # Use engagement drop as additional silence/withdrawal hint when no explicit signal.
        engagement_raw = str(s.get("engagement_level", "none")).lower()
        if engagement_raw in ("none", "low"):
            channels["silence_withdrawal"] = max(channels["silence_withdrawal"], 0.25 if engagement_raw == "low" else 0.5)

        weights = {
            "response_latency_spike": 0.20,
            "rapid_topic_switching": 0.10,
            "vocal_intensity": 0.15,
            "repetitive_language_looping": 0.10,
            "movement_acceleration": 0.15,
            "micro_frustration": 0.10,
            "interruptions": 0.10,
            "humor_deflection": 0.05,
            "silence_withdrawal": 0.10,
            "task_abandonment": 0.10,
            "facial_regulation_changes": 0.10,
            "breathing_pattern_shift": 0.10,
        }
        raw = 0.0
        total = 0.0
        for k, w in weights.items():
            raw += channels[k] * w
            total += w
        score = self._clamp(raw / max(total, 1e-6))
        if score < 0.30:
            band = "low"
        elif score <= 0.60:
            band = "rising"
        else:
            band = "high"
        return {"score": round(score, 4), "band": band, "signals": channels}

    def _infer_phase(self, engagement, cognitive_load, frustration, regulation, readiness, escalation, signals):
        band = escalation.get("band", "low")
        score = float(escalation.get("score", 0.0))
        if band == "high" or regulation == "dysregulated":
            return "recover"
        if band == "rising" and engagement in ("disengaged", "drifting") and cognitive_load in ("elevated", "high"):
            return "rest"
        if signals.get("humor_deflection", 0.0) > 0.45 or signals.get("rapid_topic_switching", 0.0) > 0.50:
            return "co_play"
        if engagement in ("disengaged",) and score < 0.30:
            return "explore"
        if engagement in ("steady", "high") and frustration == "none" and readiness == "can_increase":
            return "advance"
        if engagement in ("steady", "high") and frustration in ("none", "mild") and cognitive_load in ("workable",):
            return "practice"
        if engagement in ("steady", "drifting"):
            return "engage"
        if frustration in ("moderate", "acute"):
            return "repair"
        return "stabilize"

    def _clamp(self, value):
        try:
            v = float(value)
        except Exception:
            v = 0.0
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    def _starter_plan(self):
        anchors = self.get_or_init_profile().get("interest_anchors", [])
        theme = anchors[0] if anchors else "space"
        return [
            f"Day 1 - Draw a {theme} story",
            f"Day 2 - Trace shapes for {theme} parts",
            f"Day 3 - Count objects in a {theme} scene",
            f"Day 4 - Build a simple {theme} map",
            f"Day 5 - Label one-word {theme} items",
            f"Day 6 - Create a new {theme} character",
            f"Day 7 - Tell a short {theme} story with Bitling",
        ]

    def _derive_policy(self, traits):
        proc = traits.get("processing_latency", 0.5)
        adhd = traits.get("adhd_traits", 0.5)
        sensory = max(traits.get("sensory_audio", 0.5), traits.get("sensory_visual", 0.5))
        demand = traits.get("demand_avoidance", 0.5)
        return {
            "prompt_length_words": int(round(4 + (1.0 - proc) * 6)),
            "wait_time_seconds": round(2.0 + proc * 7.0, 2),
            "choice_count": 2 if demand > 0.7 else 3,
            "task_duration_seconds": int(round(45 + adhd * 20)),
            "visual_intensity": "calm" if sensory > 0.7 else "moderate",
            "celebration_density": "high" if adhd > 0.65 else "medium",
            "micro_tasking": bool(adhd > 0.55 or demand > 0.65),
        }

    def _to_neurodiversity_profile(self, profile):
        t = profile["traits"]
        policy = profile["policy"]
        return {
            "sensory": {
                "visual_sensitivity": "high" if t["sensory_visual"] > 0.67 else ("low" if t["sensory_visual"] < 0.34 else "medium"),
                "auditory_sensitivity": "high" if t["sensory_audio"] > 0.67 else ("low" if t["sensory_audio"] < 0.34 else "medium"),
                "preferred_visual_vibe": policy.get("visual_intensity", "calm"),
            },
            "communication": {
                "processing_type": "gestalt" if t["autism_traits"] > 0.55 else "analytic",
                "style": "declarative" if t["demand_avoidance"] > 0.5 else "interrogative",
                "literalness": "high" if t["literalness"] > 0.6 else "medium",
            },
            "engagement": {
                "interaction_frequency": "low" if t["processing_latency"] > 0.7 else "medium",
                "celebration_style": "parallel" if t["demand_avoidance"] > 0.55 else "direct",
                "routine_strictness": "high" if t["autism_traits"] > 0.6 else "medium",
            },
            "executive_function": {
                "is_adhd": t["adhd_traits"] > 0.55,
                "is_audhd": t["adhd_traits"] > 0.55 and t["autism_traits"] > 0.55,
                "focus_scaffolding": "micro_tasking" if policy.get("micro_tasking", False) else "broad_guidance",
                "dopamine_optimized": t["adhd_traits"] > 0.5,
                "body_doubling_mode": t["adhd_traits"] > 0.55,
                "time_awareness": "visual_countdown",
            },
            "adaptation_policy": policy,
        }

    def _default_profile(self):
        return {
            "traits": {
                "sensory_audio": 0.5,
                "sensory_visual": 0.5,
                "processing_latency": 0.5,
                "literalness": 0.6,
                "demand_avoidance": 0.5,
                "frustration_recovery": 0.5,
                "motor_variability": 0.5,
                "attention_shift_rate": 0.5,
                "autism_traits": 0.5,
                "adhd_traits": 0.5,
            },
            "interest_anchors": self.config.get("child", {}).get("interests", ["trains", "dinosaurs"]),
            "parent_notes": {},
            "source": "default",
            "updated_at": time.time(),
            "policy": {},
            "neurodiversity_profile": {},
        }
