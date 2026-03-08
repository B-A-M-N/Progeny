import json
import os
from typing import Dict, Tuple, Optional

try:
    from jsonschema import Draft202012Validator
except Exception:
    Draft202012Validator = None


class WSContracts:
    _validators: Dict[str, object] = {}
    _schemas: Dict[str, dict] = {}
    _loaded: bool = False

    SCHEMA_BY_TYPE = {
        "get_onboarding_script": "get_onboarding_script.schema.json",
        "get_world_state": "get_world_state.schema.json",
        "set_parent_baseline": "set_parent_baseline.schema.json",
        "onboarding_event": "onboarding_event.schema.json",
        "finish_onboarding": "finish_onboarding.schema.json",
        "start_media_session": "start_media_session.schema.json",
        "media_probe_event": "media_probe_event.schema.json",
        "end_media_session": "end_media_session.schema.json",
        "get_media_insights": "get_media_insights.schema.json",
        "get_media_probe_pack": "get_media_probe_pack.schema.json",
        "regulation_signal": "regulation_signal.schema.json",
        "world_action": "world_action.schema.json",
    }

    @classmethod
    def _contracts_dir(cls) -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, "..", "contracts", "ws"))

    @classmethod
    def load(cls):
        if cls._loaded:
            return
        cls._loaded = True
        base = cls._contracts_dir()
        for msg_type, fname in cls.SCHEMA_BY_TYPE.items():
            path = os.path.join(base, fname)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            cls._schemas[msg_type] = schema
            if Draft202012Validator:
                cls._validators[msg_type] = Draft202012Validator(schema)

    @classmethod
    def validate_message(cls, payload: dict) -> Tuple[bool, Optional[str]]:
        cls.load()
        if not isinstance(payload, dict):
            return False, "message must be a JSON object"
        msg_type = str(payload.get("type", "")).strip()
        if not msg_type:
            return False, "missing required field: type"
        if msg_type not in cls._schemas:
            # Unmapped message types remain pass-through for now.
            return True, None

        if msg_type in cls._validators:
            validator = cls._validators[msg_type]
            errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
            if errors:
                first = errors[0]
                path = ".".join([str(p) for p in list(first.path)]) or "root"
                return False, f"{path}: {first.message}"
            return True, None

        # Fallback when jsonschema dependency is not available.
        schema = cls._schemas[msg_type]
        return cls._fallback_validate(payload, schema)

    @classmethod
    def _fallback_validate(cls, payload: dict, schema: dict) -> Tuple[bool, Optional[str]]:
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                return False, f"missing required field: {key}"
        props = schema.get("properties", {})
        for key, rule in props.items():
            if key not in payload:
                continue
            val = payload[key]
            ok, reason = cls._check_rule(val, rule)
            if not ok:
                return False, f"{key}: {reason}"
        return True, None

    @classmethod
    def _check_rule(cls, value, rule: dict) -> Tuple[bool, Optional[str]]:
        if "const" in rule and value != rule["const"]:
            return False, f"must be {rule['const']}"
        if "enum" in rule and value not in rule["enum"]:
            return False, "value not in enum"

        t = rule.get("type")
        if t is not None:
            types = t if isinstance(t, list) else [t]
            type_ok = False
            for typ in types:
                if typ == "string" and isinstance(value, str):
                    type_ok = True
                elif typ == "object" and isinstance(value, dict):
                    type_ok = True
                elif typ == "array" and isinstance(value, list):
                    type_ok = True
                elif typ in ("number", "integer") and isinstance(value, (int, float)):
                    type_ok = True
                elif typ == "boolean" and isinstance(value, bool):
                    type_ok = True
            if not type_ok:
                return False, f"expected type {types}"

        if isinstance(value, str) and "minLength" in rule:
            if len(value) < int(rule["minLength"]):
                return False, f"must have minLength {rule['minLength']}"

        return True, None
