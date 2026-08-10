"""Robust JSON parsing for AI output (handles ```json fences and trailing commas)."""
from __future__ import annotations
import json
import re
from typing import Any


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Best-effort JSON extraction from model output.

    Tries: direct parse → first fenced block → first { … } span → [ … ] span.
    """
    if not text:
        raise ValueError("Empty response from LLM")
    try:
        return json.loads(text)
    except Exception:
        pass

    m = _FENCE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # First balanced JSON object
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    snippet = text[start:i + 1]
                    try:
                        return json.loads(snippet)
                    except Exception:
                        break
    raise ValueError(f"Could not parse JSON from LLM response (first 200 chars): {text[:200]!r}")
