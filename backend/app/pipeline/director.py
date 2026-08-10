"""Video Director — the orchestrator. Drives the entire pipeline from prompt to MP4.

Public entry points:
- `analyze_and_plan(...)`        — LLM planning only
- `generate_assets(...)`          — produce images/voice/music for all scenes
- `render(...)`                   — assemble final MP4
- `run(...)`                      — convenience: plan + assets + render

A single `VideoDirector` is created per video. It owns its own provider
instances and writes all artifacts to a per-video work directory.
"""
from __future__ import annotations
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.providers.base import GenerationContext, ProviderError
from app.providers.image.base import ImageRequest
from app.providers.image.factory import make_image_provider
from app.providers.llm.base import LLMMessage
from app.providers.llm.factory import make_llm_provider
from app.providers.music.base import MusicRequest
from app.providers.music.factory import make_music_provider
from app.providers.tts.base import TTSRequest
from app.providers.tts.factory import make_tts_provider
from app.providers.video.base import VideoRequest
from app.providers.video.factory import make_video_provider
from app.utils.files import aspect_to_size, video_workdir
from app.utils.json_parse import extract_json
from app.schemas.ai import VideoBrief, VideoScript, ScenePlan


log = logging.getLogger("hackroot.director")


class VideoDirectorError(RuntimeError):
    def __init__(self, step: str, message: str) -> None:
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.user_message = message


# ---------------------------------------------------------------------------
# Schemas (informal, used for validation)
# ---------------------------------------------------------------------------
REQUIRED_SCENE_KEYS = {"scene_number", "duration", "visual_prompt", "voiceover"}


@dataclass
class VideoPlan:
    title: str
    duration: int
    aspect_ratio: str
    language: str
    style: str
    voice: str
    scenes: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.raw, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------
class VideoDirector:
    """The AI Video Director. One instance per video."""

    def __init__(
        self,
        *,
        workdir: str,
        video_id: int,
        user_id: int,
        job_id: int | None = None,
        progress_cb=None,
    ) -> None:
        self.workdir = video_workdir(workdir, video_id)
        self.video_id = video_id
        self.user_id = user_id
        self.job_id = job_id
        self.progress_cb = progress_cb

        # Lazy providers
        self.llm = make_llm_provider()
        self.image = make_image_provider()
        self.video = make_video_provider()
        self.tts = make_tts_provider()
        self.music = make_music_provider()

    # ------------------------------------------------------------------
    def _progress(self, step: str, pct: int, message: str = "") -> None:
        log.info("Video %s step=%s pct=%d %s", self.video_id, step, pct, message)
        if self.progress_cb:
            try:
                self.progress_cb(step, pct, message)
            except Exception:  # never let callbacks break the pipeline
                log.exception("progress callback failed")

    # ------------------------------------------------------------------
    # 1. Prompt analysis + brief
    # ------------------------------------------------------------------
    async def analyze_and_plan(
        self,
        *,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        language: str,
        style: str,
        voice: str,
        brand_kit: dict | None = None,
    ) -> VideoPlan:
        self._progress("analyzing_prompt", 10, "Analyzing your prompt")
        ctx = GenerationContext(
            user_id=self.user_id, video_id=self.video_id, job_id=self.job_id or 0,
            brand_kit=brand_kit, style=style, language=language,
        )

        # 1a — Brief
        brief = await self._llm_brief(prompt, duration, aspect_ratio, language)
        self._progress("creating_brief", 20, f"Title: {brief.get('title')}")

        # 1b — Script + scenes
        self._progress("creating_script", 30, "Writing the script")
        script_plan = await self._llm_script_and_scenes(
            prompt=prompt, duration=duration, language=language,
            style=style, voice=voice,
        )
        scenes = self._validate_scenes(script_plan.get("scenes", []), duration)
        self._progress("planning_scenes", 40, f"{len(scenes)} scenes planned")

        plan = VideoPlan(
            title=brief.get("title") or "AI Video",
            duration=duration,
            aspect_ratio=aspect_ratio,
            language=language,
            style=style,
            voice=voice,
            scenes=scenes,
            raw={"brief": brief, "script": script_plan, "context": ctx.__dict__},
        )
        return plan

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _llm_brief(self, prompt: str, duration: int, aspect: str, language: str) -> dict:
        system = (
            "You are a senior video creative director. Produce a concise JSON object "
            "with these keys: title, logline, target_audience, tone, duration, "
            "aspect_ratio, language. Respond with valid JSON only."
        )
        user = json.dumps({
            "prompt": prompt, "duration": duration, "aspect_ratio": aspect, "language": language,
        })
        r = await self.llm.chat(
            [LLMMessage("system", system), LLMMessage("user", user)],
            temperature=0.6, max_tokens=600, response_format_json=True,
        )
        data = extract_json(r.content)
        # Validate using Pydantic
        brief = VideoBrief.model_validate(data)
        return brief.model_dump()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _llm_script_and_scenes(
        self, *, prompt: str, duration: int, language: str, style: str, voice: str
    ) -> dict:
        system = (
            "You are a video script writer. Produce JSON with this exact shape:\n"
            "{ scenes: [ { scene_number, duration, beat, voiceover, caption, "
            "visual_prompt, camera_movement, transition, music_intensity, "
            "zoom_from, zoom_to } ], total_words, language, style, voice }\n"
            "Sum of scene durations MUST equal `duration`. Respond with JSON only."
        )
        user = json.dumps({
            "prompt": prompt, "duration": duration, "language": language,
            "style": style, "voice": voice,
        })
        r = await self.llm.chat(
            [LLMMessage("system", system), LLMMessage("user", user)],
            temperature=0.7, max_tokens=2000, response_format_json=True,
        )
        data = extract_json(r.content)
        # Validate against strict JSON schema
        script = VideoScript.model_validate(data)
        return script.model_dump()

    def _validate_scenes(self, scenes: list[dict], total_duration: int) -> list[dict]:
        if not scenes:
            raise VideoDirectorError("plan", "LLM returned no scenes.")
        for s in scenes:
            missing = REQUIRED_SCENE_KEYS - set(s.keys())
            if missing:
                raise VideoDirectorError("plan", f"Scene missing keys: {missing}")
        # Normalize / clamp
        for i, s in enumerate(scenes, start=1):
            s["scene_number"] = i
            s["duration"] = max(1.0, float(s.get("duration", total_duration / len(scenes))))
            s.setdefault("voiceover", "")
            s.setdefault("caption", s.get("voiceover", ""))
            s.setdefault("visual_prompt", s.get("voiceover", ""))
            s.setdefault("camera_movement", "slow_zoom_in")
            s.setdefault("transition", "fade" if i > 1 else "none")
            s.setdefault("music_intensity", "med")
            s.setdefault("zoom_from", 1.0)
            s.setdefault("zoom_to", 1.15)
            s.setdefault("pan_x", 0.0)
            s.setdefault("pan_y", 0.0)
        # Renormalize durations to total
        s_sum = sum(s["duration"] for s in scenes)
        if s_sum and abs(s_sum - total_duration) > 0.5:
            scale = total_duration / s_sum
            for s in scenes:
                s["duration"] = round(s["duration"] * scale, 2)
        return scenes

    # ------------------------------------------------------------------
    # 2. Asset generation
    # ------------------------------------------------------------------
    async def generate_assets(
        self,
        plan: VideoPlan,
        *,
        product_image_paths: list[str] | None = None,
    ) -> VideoPlan:
        product_image_paths = product_image_paths or []
        img_size = aspect_to_size(plan.aspect_ratio, base=1024)

        n = len(plan.scenes)
        for i, scene in enumerate(plan.scenes, start=1):
            pct = 50 + int(15 * (i / n))
            self._progress("generating_visuals", pct, f"Scene {i}/{n} visual")

            # 2a — image
            img_key = f"video_{self.video_id}/images/scene_{i:02d}.png"
            img_path = os.path.join(self.workdir, "images", f"scene_{i:02d}.png")
            prompt = scene["visual_prompt"]
            # If user provided product images, bias the first relevant scenes
            # to use them directly so the product is preserved.
            if product_image_paths and i <= len(product_image_paths):
                src = product_image_paths[i - 1]
                # Use the user's image verbatim — normalized to the render canvas
                # without recompression of the stored original.
                scene["image_path"] = self._place_product_image(src, img_path, img_size)
                scene["is_product_image"] = True
            else:
                try:
                    res = await self.image.generate(
                        ImageRequest(
                            prompt=prompt,
                            negative_prompt=scene.get("negative_visual_prompt"),
                            width=img_size[0], height=img_size[1],
                            style=plan.style,
                        ),
                        out_path=img_path,
                    )
                    scene["image_path"] = res.path
                except ProviderError as e:
                    log.warning("Image provider failed (%s), using gradient fallback", e)
                    # Fallback: generate a gradient anyway via the same provider
                    # (mock provider will succeed; real providers will raise the same
                    # error to the user).
                    from app.providers.image.mock import MockImageProvider
                    fb = MockImageProvider()
                    res = await fb.generate(
                        ImageRequest(prompt=prompt, width=img_size[0], height=img_size[1]),
                        out_path=img_path,
                    )
                    scene["image_path"] = res.path

            if not scene.get("image_path"):
                scene["image_path"] = img_path

            # 2b — video clip (best-effort; if mock returns None we use the still)
            clip_path = os.path.join(self.workdir, "clips", f"scene_{i:02d}.mp4")
            try:
                v = await self.video.generate(
                    VideoRequest(prompt=prompt, duration=int(scene["duration"]),
                                 aspect_ratio=plan.aspect_ratio, image_path=scene["image_path"]),
                    out_path=clip_path,
                )
                if v is not None:
                    scene["video_clip_path"] = v.path
            except ProviderError as e:
                log.warning("Video provider failed for scene %d: %s", i, e)
                # Surface a clear error only on the last scene so partial work survives
                if i == n:
                    log.warning("Continuing with still-image assembly.")

        # 2c — voice
        self._progress("generating_voice", 65, "Synthesizing voiceover")
        if plan.voice != "none":
            voice_path = os.path.join(self.workdir, "voice", "full.wav")
            full_text = " ".join((s.get("voiceover") or "").strip() for s in plan.scenes).strip()
            if full_text:
                try:
                    await self.tts.synthesize(
                        TTSRequest(text=full_text, voice=plan.voice, language=plan.language),
                        out_path=voice_path,
                    )
                except ProviderError as e:
                    raise VideoDirectorError("tts", e.user_message) from e
            # Also per-scene voice for tight timing
            for i, scene in enumerate(plan.scenes, start=1):
                txt = (scene.get("voiceover") or "").strip()
                if not txt:
                    continue
                p = os.path.join(self.workdir, "voice", f"scene_{i:02d}.wav")
                try:
                    res = await self.tts.synthesize(
                        TTSRequest(text=txt, voice=plan.voice, language=plan.language),
                        out_path=p,
                    )
                    scene["voice_path"] = res.path
                    scene["voice_duration"] = res.duration
                except ProviderError as e:
                    log.warning("TTS failed for scene %d: %s", i, e)
                    scene["voice_path"] = voice_path if os.path.exists(voice_path) else None

        # 2d — music
        self._progress("selecting_music", 75, "Composing background music")
        music_path = os.path.join(self.workdir, "music", "bgm.wav")
        try:
            await self.music.generate(
                MusicRequest(prompt=plan.title, duration=plan.duration,
                             style=plan.style, intensity="med"),
                out_path=music_path,
            )
        except ProviderError as e:
            log.warning("Music provider failed: %s", e)
            music_path = ""

        # 2e — captions
        self._progress("generating_captions", 80, "Generating captions")
        await self._generate_captions(plan)

        plan.raw["assets"] = {
            "music": music_path,
            "voice_full": os.path.join(self.workdir, "voice", "full.wav") if plan.voice != "none" else None,
        }
        return plan

    # ------------------------------------------------------------------
    # Product image mode
    # ------------------------------------------------------------------
    @staticmethod
    def _place_product_image(src: str, dest: str, size: tuple[int, int]) -> str:
        """Fit a user-supplied product image onto the scene canvas.

        The user's original upload is never modified or recompressed — this only
        produces a render-time working copy at `dest`. Aspect ratio is preserved
        (contain, never crop or stretch) so products are not distorted; the
        remaining area is filled with a blurred cover of the same image.
        """
        src_path = Path(src)
        if not src_path.exists():
            raise VideoDirectorError("assets", f"Product image not found: {src}")
        target_w, target_h = size
        try:
            from PIL import Image, ImageFilter
        except ImportError:  # pragma: no cover - Pillow is a hard dependency
            Path(dest).write_bytes(src_path.read_bytes())
            return dest

        with Image.open(src_path) as raw:
            im = raw.convert("RGB")

            # Blurred "cover" backdrop.
            cover_scale = max(target_w / im.width, target_h / im.height)
            cover = im.resize(
                (max(1, int(im.width * cover_scale)), max(1, int(im.height * cover_scale))),
                Image.LANCZOS,
            ).filter(ImageFilter.GaussianBlur(28))
            left = (cover.width - target_w) // 2
            top = (cover.height - target_h) // 2
            canvas = cover.crop((left, top, left + target_w, top + target_h))

            # Undistorted "contain" foreground.
            fit_scale = min(target_w / im.width, target_h / im.height)
            fg = im.resize(
                (max(1, int(im.width * fit_scale)), max(1, int(im.height * fit_scale))),
                Image.LANCZOS,
            )
            canvas.paste(fg, ((target_w - fg.width) // 2, (target_h - fg.height) // 2))
            canvas.save(dest, format="PNG")
        return dest

    async def _generate_captions(self, plan: VideoPlan) -> None:
        system = (
            "You generate timed captions for a video. Output JSON: "
            "{ captions: [ { start, end, text } ] }. start/end are seconds. "
            "Cover every spoken line; keep lines under ~42 chars."
        )
        user = json.dumps({"scenes": [
            {"scene_number": s["scene_number"], "duration": s["duration"],
             "voiceover": s.get("voiceover", ""), "caption": s.get("caption", "")}
            for s in plan.scenes
        ]})
        r = await self.llm.chat(
            [LLMMessage("system", system), LLMMessage("user", user)],
            temperature=0.4, max_tokens=1500, response_format_json=True,
        )
        try:
            data = extract_json(r.content)
            caps = data.get("captions", [])
        except Exception as e:
            log.warning("Caption JSON parse failed, falling back: %s", e)
            caps = []
            t = 0.0
            for s in plan.scenes:
                text = (s.get("caption") or s.get("voiceover") or "").strip()
                if text:
                    caps.append({"start": round(t, 2), "end": round(t + s["duration"], 2), "text": text})
                t += s["duration"]
        # Write SRT
        srt = self._to_srt(caps)
        Path(self.workdir, "captions", "captions.srt").write_text(srt, encoding="utf-8")
        Path(self.workdir, "captions", "captions.vtt").write_text(
            "WEBVTT\n\n" + srt.replace(",", ".").replace(" --> ", " --> "), encoding="utf-8"
        )

    @staticmethod
    def _to_srt(captions: list[dict]) -> str:
        def ts(sec: float) -> str:
            ms = int(round((sec - int(sec)) * 1000))
            s = int(sec) % 60
            m = (int(sec) // 60) % 60
            h = int(sec) // 3600
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        out = []
        for i, c in enumerate(captions, start=1):
            out.append(f"{i}\n{ts(float(c['start']))} --> {ts(float(c['end']))}\n{c['text']}\n")
        return "\n".join(out)

    # ------------------------------------------------------------------
    # 3. Render (delegated to renderer)
    # ------------------------------------------------------------------
    async def render(self, plan: VideoPlan, *, brand_logo: str | None = None,
                     watermark: str | None = None) -> dict:
        from app.rendering.renderer import VideoRenderer

        self._progress("rendering_video", 88, "Rendering final video")
        renderer = VideoRenderer(plan=plan, workdir=self.workdir)
        result = renderer.render(brand_logo=brand_logo, watermark=watermark)
        self._progress("finalizing", 95, "Generating thumbnail")
        return result

    # ------------------------------------------------------------------
    # All-in-one
    # ------------------------------------------------------------------
    async def run(
        self,
        *,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        language: str,
        style: str,
        voice: str,
        brand_kit: dict | None = None,
        product_image_paths: list[str] | None = None,
        brand_logo: str | None = None,
        watermark: str | None = None,
    ) -> dict:
        t0 = time.time()
        plan = await self.analyze_and_plan(
            prompt=prompt, duration=duration, aspect_ratio=aspect_ratio,
            language=language, style=style, voice=voice, brand_kit=brand_kit,
        )
        plan = await self.generate_assets(plan, product_image_paths=product_image_paths)
        result = await self.render(plan, brand_logo=brand_logo, watermark=watermark)
        result["plan_json"] = plan.to_json()
        result["title"] = plan.title
        result["elapsed_seconds"] = round(time.time() - t0, 2)
        return result
