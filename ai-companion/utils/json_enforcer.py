import json
import re
from typing import Type, TypeVar, Any, Dict, Optional, List
from pydantic import BaseModel, ValidationError
from json_repair import repair_json

T = TypeVar("T", bound=BaseModel)

class JsonEnforcer:
    @staticmethod
    def extract_json_block(text: str) -> str:
        """
        Extracts the first JSON block found in the text.
        Handles markdown code blocks and raw JSON.
        """
        # Try finding markdown JSON block
        markdown_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if markdown_match:
            return markdown_match.group(1)
        
        # Try finding the first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        
        return text

    @classmethod
    def enforce(cls, text: str, schema: Type[T], default_factory=None) -> T:
        """
        The "Iron Gate" enforcer. 
        Extracts, repairs (using json-repair), parses, validates, and provides a safe fallback.
        """
        # 1. Block Extraction
        json_str = cls.extract_json_block(text)
        
        # 2. Aggressive Repair (handles missing quotes, trailing commas, unclosed braces)
        repaired_json = repair_json(json_str)
        
        try:
            # 3. Standard JSON Load
            data = json.loads(repaired_json)
            
            # 4. Pydantic Validation & Coercion
            return schema.model_validate(data)
            
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[JsonEnforcer] Iron Gate failed for {schema.__name__}: {e}")
            print(f"[JsonEnforcer] Raw text: {text[:100]}...")
            
            if default_factory:
                return default_factory()
            
            # Final fallback: Try to create a default model instance if possible
            try:
                return schema.model_validate({})
            except ValidationError:
                # If even that fails, we can't do anything else safely
                raise ValueError(f"CRITICAL: Could not enforce schema {schema.__name__} and no safe default exists.")

def fuzzy_enum_match(value: str, allowed_values: List[str], default: str) -> str:
    """
    Map diverse model vocabulary to strict system enums.
    Example: "super excited" -> "excited"
    """
    val_lower = str(value).lower()
    for allowed in allowed_values:
        if allowed in val_lower:
            return allowed
    return default

def fuzzy_enum_match(value: str, allowed_values: List[str], default: str) -> str:
    """
    Map diverse model vocabulary to strict system enums.
    Example: "super excited" -> "excited"
    """
    val_lower = str(value).lower()
    for allowed in allowed_values:
        if allowed in val_lower:
            return allowed
    return default
