"""Mock LLM provider — produces structured JSON for testing without API keys.

The mock uses simple heuristics to produce a reasonable video plan from a prompt.
It is *not* used in production unless explicitly selected. It is, however, the
default fallback when no real LLM key is configured, so the rest of the pipeline
is end-to-end runnable out of the box.
"""
from __future__ import annotations
import json
import re
from typing import Iterable

from app.providers.base import ProviderError
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse


def _extract_title_and_topic(prompt: str) -> tuple[str, str]:
    p = prompt.strip()
    # Try patterns like "Create a ... video for <Brand>"
    m = re.search(r"for ([A-Z][\w&' ]{1,60})", p)
    brand = (m.group(1).strip().rstrip(".") if m else "Our Brand").split()[0:3]
    title = " ".join(brand).title() or "AI Video"
    return title, p


def _word_target_for(duration: int) -> int:
    # ~2.6 words/sec for natural English; round to nearest 5
    return max(15, round((duration * 2.6) / 5) * 5)


def _scene_split(duration: int) -> list[float]:
    if duration <= 6:
        return [duration]
    if duration <= 15:
        return [round(duration / 2, 1), round(duration / 2, 1)]
    if duration <= 30:
        # 4 scenes weighted: hook(0.2), showcase(0.3), features(0.3), cta(0.2)
        return [round(duration * 0.2, 1), round(duration * 0.3, 1),
                round(duration * 0.3, 1), round(duration * 0.2, 1)]
    # 60s — 5 scenes
    return [round(duration * 0.15, 1), round(duration * 0.25, 1),
            round(duration * 0.25, 1), round(duration * 0.20, 1),
            round(duration * 0.15, 1)]


def _slug_brand(prompt: str) -> str:
    m = re.search(r"for ([A-Z][\w&' ]{1,60})", prompt)
    return (m.group(1).strip() if m else "the brand").rstrip(".")


class MockLLMProvider(LLMProvider):
    """Deterministic, key-free LLM for development and tests.

    Produces well-formed JSON for all of the planning prompts the pipeline sends.
    """

    name = "mock"

    async def chat(
        self,
        messages: Iterable[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format_json: bool = False,
    ) -> LLMResponse:
        msgs = list(messages)
        system = (msgs[0].content if msgs and msgs[0].role == "system" else "").lower()
        user = msgs[-1].content if msgs else ""

        # Decide which planner is being called by keywords in the system prompt.
        # Route on the distinctive keys each planner asks the model to return,
        # which is far more robust than matching prose in the system prompt.
        if "logline" in system and "aspect_ratio" in system:
            payload = self._brief(user)
        elif "scenes" in system and ("voiceover" in system or "visual_prompt" in system):
            payload = self._script_and_scenes(user)
        elif "negative_prompt" in system or "scene visual" in system:
            payload = self._scene_prompts(user)
        elif "caption" in system:
            payload = self._captions(user)
        else:
            payload = {"text": self._generic(user)}

        if response_format_json:
            return LLMResponse(content=json.dumps(payload, ensure_ascii=False), model="mock-llm")
        return LLMResponse(content=json.dumps(payload, ensure_ascii=False), model="mock-llm")

    # --- planners ---------------------------------------------------------

    def _brief(self, prompt_payload: str) -> dict:
        try:
            data = json.loads(prompt_payload)
        except Exception:
            data = {"prompt": prompt_payload}
        prompt = data.get("prompt", prompt_payload)
        title, topic = _extract_title_and_topic(prompt)
        return {
            "title": title,
            "logline": topic[:160],
            "target_audience": "general",
            "tone": "energetic and professional",
            # Echo back what the director actually asked for.
            "duration": int(data.get("duration") or 20),
            "aspect_ratio": data.get("aspect_ratio") or "9:16",
            "language": data.get("language") or "English",
        }

    def _script_and_scenes(self, prompt_payload: str) -> dict:
        # prompt_payload is a JSON-ish string from the pipeline; we tolerate
        # either raw JSON or a plain text fallback.
        try:
            data = json.loads(prompt_payload)
        except Exception:
            data = {"prompt": prompt_payload, "duration": 20, "language": "English",
                    "style": "Cinematic", "voice": "female"}

        duration = int(data.get("duration") or 20)
        language = data.get("language", "English")
        style = data.get("style", "Cinematic")
        voice = data.get("voice", "female")
        prompt = data.get("prompt", "")
        brand = _slug_brand(prompt)
        words = _word_target_for(duration)
        scenes_n = len(_scene_split(duration))

        # Build scenes
        beats = ["Hook", "Showcase", "Features", "Call to Action"]
        if scenes_n == 1:
            beats = ["Spotlight"]
        elif scenes_n == 2:
            beats = ["Hook", "Call to Action"]
        elif scenes_n == 5:
            beats = ["Hook", "Showcase", "Detail", "Benefits", "Call to Action"]
        beats = beats[:scenes_n]

        durations = _scene_split(duration)
        # Distribute words roughly proportionally
        scenes = []
        remaining = words
        for i, beat in enumerate(beats):
            share = round(words * (durations[i] / duration) / 5) * 5
            share = max(6, min(share, remaining))
            remaining -= share
            scenes.append({
                "scene_number": i + 1,
                "duration": round(durations[i], 1),
                "beat": beat,
                "voiceover": self._voice_line(beat, brand, language, share),
                "caption": self._caption(beat, brand, language),
                "visual_prompt": self._visual_prompt(beat, brand, style, prompt),
                "camera_movement": "slow_zoom_in" if beat != "Call to Action" else "static",
                "transition": "fade" if i > 0 else "none",
                "music_intensity": "high" if beat in ("Hook", "Call to Action") else "med",
                "zoom_from": 1.0,
                "zoom_to": 1.15,
            })

        # Make sure durations sum exactly
        drift = round(duration - sum(s["duration"] for s in scenes), 1)
        if scenes and drift:
            scenes[-1]["duration"] = round(scenes[-1]["duration"] + drift, 1)

        return {"scenes": scenes, "total_words": words, "language": language,
                "style": style, "voice": voice}

    def _scene_prompts(self, prompt_payload: str) -> dict:
        try:
            data = json.loads(prompt_payload)
        except Exception:
            data = {"scenes": []}
        for s in data.get("scenes", []):
            s.setdefault("negative_prompt", "blurry, low quality, distorted, watermark")
        return data

    def _captions(self, prompt_payload: str) -> dict:
        try:
            data = json.loads(prompt_payload)
        except Exception:
            return {"captions": []}
        captions = []
        t = 0.0
        for s in data.get("scenes", []):
            text = (s.get("caption") or s.get("voiceover") or "").strip()
            if not text:
                t += float(s.get("duration", 0))
                continue
            # One caption per scene
            captions.append({"start": round(t, 2), "end": round(t + float(s["duration"]), 2), "text": text})
            t += float(s["duration"])
        return {"captions": captions}

    def _generic(self, prompt: str) -> str:
        return f"OK: {prompt[:200]}"

    # --- copy helpers -----------------------------------------------------

    def _voice_line(self, beat: str, brand: str, language: str, words: int) -> str:
        en = {
            "Hook":          f"Meet {brand} — a whole new way to stand out.",
            "Showcase":      f"Designed with care, made for everyday life.",
            "Features":      f"Quality you can see, comfort you can feel.",
            "Detail":        f"Crafted down to the smallest detail.",
            "Benefits":      f"Built to last, made to love.",
            "Call to Action": f"Order yours today and feel the difference.",
            "Spotlight":     f"Discover {brand}.",
        }
        hi = {
            "Hook":          f"{brand} se miliye — bilkul naya andaaz.",
            "Showcase":      f"Har baar ke liye bana, har pal ke liye perfect.",
            "Features":      f"Quality dikhti hai, comfort mehsoos hota hai.",
            "Detail":        f"Har detail pe dhyan diya gaya hai.",
            "Benefits":      f"Lambi umar, pyara design.",
            "Call to Action": f"Aaj hi order karein aur khud feel karein.",
            "Spotlight":     f"{brand} ko discover karein.",
        }
        table = hi if language.lower().startswith("hind") else en
        line = table.get(beat, table["Showcase"])
        # Pad / trim roughly to words
        w = line.split()
        if len(w) < words:
            w += ["today.", "experience", "the", "difference", "now."][: words - len(w)]
        return " ".join(w[: max(4, words)])

    def _caption(self, beat: str, brand: str, language: str) -> str:
        en = {"Hook": f"✨ {brand}", "Showcase": "Made for you", "Features": "Quality & Comfort",
              "Detail": "Crafted with care", "Benefits": "Built to last",
              "Call to Action": "Order now 👇", "Spotlight": f"{brand}"}
        hi = {"Hook": f"✨ {brand}", "Showcase": "Aapke liye bana", "Features": "Quality & Comfort",
              "Detail": "Har detail pe dhyan", "Benefits": "Lambi umar",
              "Call to Action": "Abhi order karein 👇", "Spotlight": f"{brand}"}
        table = hi if language.lower().startswith("hind") else en
        return table.get(beat, beat)

    def _visual_prompt(self, beat: str, brand: str, style: str, user_prompt: str) -> str:
        base = user_prompt.replace("\n", " ")[:200]
        if beat == "Hook":
            return f"Cinematic {style} hero shot of {brand}, dramatic lighting, shallow depth of field, vibrant colors, premium feel, vertical 9:16"
        if beat == "Showcase":
            return f"Product showcase of {brand}, clean studio backdrop, soft rim light, vertical composition, professional product photography"
        if beat in ("Features", "Detail", "Benefits"):
            return f"Close-up detail shot of {brand}, highlighting quality and craftsmanship, macro lens, soft natural light, premium aesthetic"
        if beat == "Call to Action":
            return f"Clean brand-focused closing frame of {brand}, bold typography space, gradient backdrop matching brand colors, vertical 9:16"
        return f"{style} cinematic frame about: {base}"
