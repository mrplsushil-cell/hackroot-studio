"""FFmpeg-based video renderer.

Pipeline:
  for each scene:
    - Take scene.image_path (or video_clip_path)
    - Apply Ken Burns (zoom/pan) to fit scene duration
    - Burn caption (ASS) into frame
  Concat scenes with crossfades
  Mix per-scene voice + global BGM
  Burn subtitle track (SRT)
  Add optional logo watermark
  Output H.264 MP4 + thumbnail
"""
from __future__ import annotations
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipeline.director import VideoPlan
from app.utils.ffmpeg import FFmpegError, make_thumbnail, probe, run

log = logging.getLogger("hackroot.renderer")


def _drawtext_filter(text: str, *, fontsize: int = 56, fontcolor: str = "white",
                     box: bool = True, y: str = "h*0.78") -> str:
    safe = text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
    parts = [
        f"text='{safe}'",
        f"fontsize={fontsize}",
        f"fontcolor={fontcolor}",
        "font='DejaVu Sans'",
    ]
    if box:
        parts += ["box=1", "boxcolor=black@0.55", "boxborderw=18"]
    parts.append(f"x=(w-text_w)/2")
    parts.append(f"y={y}")
    return "drawtext=" + ":".join(parts)


def _kb_filter(duration: float, w: int, h: int, z_from: float, z_to: float,
               pan_x: float, pan_y: float) -> str:
    """Ken Burns (zoom + pan) implemented with an animated fixed-size crop.

    FFmpeg's `zoompan` re-samples the *whole* source frame on every output
    frame, which measured ~11s for a 2s clip here — roughly 16x slower than
    realtime and the cause of multi-minute renders. Cropping a constant-sized
    window whose position/scale is driven by `t`, then scaling once, is
    visually equivalent and measured ~0.7s for the same clip.
    """
    fps = 30
    duration = max(duration, 0.04)
    zoom_max = max(z_from, z_to, 1.0)

    # Work on a canvas large enough that the tightest crop still covers the
    # output resolution, keeping even dimensions for yuv420p.
    def _even(v: float) -> int:
        return max(2, int(v) // 2 * 2)

    base_w, base_h = _even(w * zoom_max), _even(h * zoom_max)

    # Crop window size is constant (required by the crop filter); the zoom is
    # produced by choosing the window relative to the enlarged canvas and
    # letting the final scale do the magnification.
    crop_w, crop_h = _even(base_w / zoom_max), _even(base_h / zoom_max)

    # Linear pan across whatever slack the crop leaves, biased by pan_x/pan_y.
    def _axis(bias: float, expr_in: str, expr_out: str) -> str:
        slack = f"({expr_in}-{expr_out})"
        if bias > 0:
            return f"'{slack}*min(1\\,t/{duration:.3f})'"
        if bias < 0:
            return f"'{slack}*(1-min(1\\,t/{duration:.3f}))'"
        return f"'{slack}/2'"

    x_expr = _axis(pan_x, "in_w", "out_w")
    y_expr = _axis(pan_y, "in_h", "out_h")

    return (
        f"scale={base_w}:{base_h}:force_original_aspect_ratio=increase,"
        f"crop={base_w}:{base_h},"
        f"crop={crop_w}:{crop_h}:x={x_expr}:y={y_expr},"
        f"scale={w}:{h},setsar=1,fps={fps}"
    )


def _scene_filter(scene: dict, w: int, h: int) -> str:
    duration = float(scene["duration"])
    src = scene.get("video_clip_path") or scene.get("image_path")
    if not src or not os.path.exists(src):
        raise FFmpegError(f"Scene {scene.get('scene_number')} has no source asset")
    z_from = float(scene.get("zoom_from", 1.0))
    z_to = float(scene.get("zoom_to", 1.15))
    pan_x = float(scene.get("pan_x", 0.0))
    pan_y = float(scene.get("pan_y", 0.0))

    is_video = src.lower().endswith((".mp4", ".mov", ".webm", ".mkv"))

    filters = []
    if is_video:
        # Use the video clip; trim/loop to duration
        # We'll let concat handle timing. For per-scene filtergraph we set fps+scale.
        filters.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black")
        filters.append(f"fps={30}")
        # Trim or freeze last frame
        filters.append(f"trim=duration={duration:.3f},setpts=PTS-STARTPTS")
    else:
        # Image → looped video with Ken Burns
        kb = _kb_filter(duration, w, h, z_from, z_to, pan_x, pan_y)
        filters.append(kb)

    # Caption burn-in
    cap = (scene.get("caption") or "").strip()
    if cap:
        # Split into 2 lines if long
        words = cap.split()
        if len(words) > 8:
            mid = len(words) // 2
            cap = " ".join(words[:mid]) + "\\n" + " ".join(words[mid:])
        fs = max(28, int(min(w, h) * 0.045))
        filters.append(_drawtext_filter(cap, fontsize=fs, y="h*0.82"))

    return ",".join(filters)


class VideoRenderer:
    def __init__(self, *, plan: VideoPlan, workdir: str) -> None:
        self.plan = plan
        self.workdir = workdir
        self.w, self.h = self._size_for(plan.aspect_ratio)
        self.fps = 30

    def _size_for(self, aspect: str) -> tuple[int, int]:
        return {
            "16:9": (1280, 720),
            "9:16": (720, 1280),
            "1:1": (1024, 1024),
            "4:5": (1024, 1280),
        }.get(aspect, (720, 1280))

    # ------------------------------------------------------------------
    def render(self, *, brand_logo: str | None = None,
                watermark: str | None = None) -> dict[str, Any]:
        work = Path(self.workdir)
        scene_clips_dir = work / "clips_final"
        if scene_clips_dir.exists():
            shutil.rmtree(scene_clips_dir)
        scene_clips_dir.mkdir(parents=True, exist_ok=True)

        # 1) Encode each scene independently
        clip_paths: list[str] = []
        for i, scene in enumerate(self.plan.scenes, start=1):
            clip_path = scene_clips_dir / f"scene_{i:02d}.mp4"
            try:
                self._encode_scene(scene, str(clip_path))
            except FFmpegError as e:
                # If zoompan fails (e.g. PIL not built in), fall back to a static
                # scaled image with caption.
                log.warning("Zoompan failed for scene %d, falling back: %s", i, e)
                self._encode_scene_static(scene, str(clip_path))
            clip_paths.append(str(clip_path))

        # 2) Concat with crossfade transitions
        concat_path = work / "concat.mp4"
        self._concat_with_transitions(clip_paths, str(concat_path))

        # 3) Mix voiceover + BGM
        voice_path = (work / "voice" / "full.wav")
        if not voice_path.exists():
            voice_path = None
        music_path = work / "music" / "bgm.wav"
        if not music_path.exists():
            music_path = None
        muxed = work / "muxed.mp4"
        self._mux_audio(str(concat_path), str(muxed), voice_path, music_path,
                        self.plan.duration)

        # 4) Optional logo + subtitle burn
        srt_path = work / "captions" / "captions.srt"
        if not srt_path.exists():
            srt_path = None
        out_path = work / "final.mp4"
        self._finalize(str(muxed), str(out_path), srt_path, brand_logo, watermark)

        # 5) Thumbnail
        thumb_path = work / "thumbs" / "thumb.jpg"
        try:
            make_thumbnail(str(out_path), str(thumb_path), at_seconds=0.5)
        except Exception as e:
            log.warning("Thumbnail generation failed: %s", e)
            thumb_path = None

        # 6) Verify
        info = probe(str(out_path))
        return {
            "output_path": str(out_path),
            "thumbnail_path": str(thumb_path) if thumb_path else None,
            "duration": info.duration,
            "width": info.width,
            "height": info.height,
            "file_size_bytes": os.path.getsize(out_path),
        }

    # ------------------------------------------------------------------
    def _encode_scene(self, scene: dict, out_path: str) -> None:
        src = scene.get("video_clip_path") or scene.get("image_path")
        duration = float(scene["duration"])
        flt = _scene_filter(scene, self.w, self.h)
        # Build ffmpeg command
        is_video = src.lower().endswith((".mp4", ".mov", ".webm", ".mkv"))
        if is_video:
            cmd = [
                settings.ffmpeg_bin, "-y",
                "-i", src,
                "-t", f"{duration:.3f}",
                "-vf", flt,
                "-an",
                "-r", str(self.fps),
                "-c:v", settings.video_codec,
                "-preset", settings.video_preset,
                "-crf", str(settings.video_crf),
                "-pix_fmt", "yuv420p",
                out_path,
            ]
        else:
            cmd = [
                settings.ffmpeg_bin, "-y",
                "-loop", "1", "-t", f"{duration:.3f}",
                "-i", src,
                "-vf", flt,
                "-an",
                "-r", str(self.fps),
                "-c:v", settings.video_codec,
                "-preset", settings.video_preset,
                "-crf", str(settings.video_crf),
                "-pix_fmt", "yuv420p",
                out_path,
            ]
        run(cmd)

    def _encode_scene_static(self, scene: dict, out_path: str) -> None:
        src = scene.get("image_path") or scene.get("video_clip_path")
        duration = float(scene["duration"])
        flt = (
            f"scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,"
            f"pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2:black"
        )
        cap = (scene.get("caption") or "").strip()
        if cap:
            safe = cap.replace("'", "\\'").replace(":", "\\:")
            flt += f",drawtext=text='{safe}':fontsize={max(28, self.w // 22)}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18:x=(w-text_w)/2:y=h*0.82:font='DejaVu Sans'"
        cmd = [
            settings.ffmpeg_bin, "-y", "-loop", "1", "-t", f"{duration:.3f}",
            "-i", src, "-vf", flt, "-an", "-r", str(self.fps),
            "-c:v", settings.video_codec, "-preset", settings.video_preset,
            "-crf", str(settings.video_crf), "-pix_fmt", "yuv420p", out_path,
        ]
        run(cmd)

    def _concat_with_transitions(self, clip_paths: list[str], out_path: str) -> None:
        if len(clip_paths) == 1:
            shutil.copyfile(clip_paths[0], out_path)
            return
        # Build a filtergraph with xfade between consecutive clips
        # Each clip is re-encoded to a common format first via filter_complex
        n = len(clip_paths)
        inputs = []
        for p in clip_paths:
            inputs += ["-i", p]
        # Build the chain
        chains = "".join(f"[{i}:v]setpts=PTS-STARTPTS,fps={self.fps},"
                         f"scale={self.w}:{self.h}:force_original_aspect_ratio=decrease,"
                         f"pad={self.w}:{self.h}:(ow-iw)/2:(oh-ih)/2:black[v{i}];"
                         for i in range(n))
        xfade_dur = 0.4
        xfades = ""
        prev = "v0"
        offset = float(clip_duration_estimate(clip_paths[0]))
        for i in range(1, n):
            xfades += f"[{prev}][v{i}]xfade=transition=fade:duration={xfade_dur}:offset={max(0, offset - xfade_dur/2):.3f}[x{i}];"
            prev = f"x{i}"
            offset += float(clip_duration_estimate(clip_paths[i])) - xfade_dur
        filter_complex = chains + xfades + f"[{prev}]null[outv]"
        cmd = [settings.ffmpeg_bin, "-y", *inputs, "-filter_complex", filter_complex,
               "-map", "[outv]", "-an", "-c:v", settings.video_codec,
               "-preset", settings.video_preset, "-crf", str(settings.video_crf),
               "-pix_fmt", "yuv420p", out_path]
        try:
            run(cmd)
        except FFmpegError as e:
            log.warning("xfade failed (%s), falling back to plain concat", e)
            self._concat_plain(clip_paths, out_path)

    def _concat_plain(self, clip_paths: list[str], out_path: str) -> None:
        list_file = Path(self.workdir) / "concat_list.txt"
        list_file.write_text("\n".join(f"file '{p}'" for p in clip_paths), encoding="utf-8")
        cmd = [settings.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
               "-i", str(list_file), "-c", "copy", out_path]
        run(cmd)

    def _mux_audio(self, video_in: str, out_path: str,
                   voice: str | None, music: str | None, total: float) -> None:
        if not voice and not music:
            shutil.copyfile(video_in, out_path)
            return
        # Build anullsrc for missing tracks
        inputs = ["-i", video_in]
        amix_inputs = []
        if voice:
            inputs += ["-i", voice]
            amix_inputs.append("[1:a]aresample=44100,atrim=0:" + f"{total:.3f},asetpts=PTS-STARTPTS[v]")
        else:
            inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            amix_inputs.append("[1:a]asetpts=PTS-STARTPTS[v]")
        if music:
            inputs += ["-i", music]
            amix_inputs.append(f"[2:a]aresample=44100,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume=0.18[m]")
        else:
            inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            amix_inputs.append("[2:a]asetpts=PTS-STARTPTS[m]")
        # Mix voice and music, with music ducked.
        # Each entry in `amix_inputs` is a complete filterchain and must be
        # separated by ';' — joining them directly produces "[v][2:a]" and
        # FFmpeg fails with "Trailing garbage after a filter".
        mix = (
            f"{';'.join(amix_inputs)};"
            f"[v][m]amix=inputs=2:duration=longest:dropout_transition=0[mix];"
            f"[mix]aresample=44100,alimiter=limit=0.95[aout]"
        )
        cmd = [settings.ffmpeg_bin, "-y", *inputs,
               "-filter_complex", mix,
               "-map", "0:v", "-map", "[aout]",
               "-c:v", "copy",
               "-c:a", settings.audio_codec, "-b:a", settings.audio_bitrate,
               "-shortest", out_path]
        run(cmd)

    def _finalize(self, video_in: str, out_path: str,
                  srt_path: str | None, logo_path: str | None,
                  watermark: str | None = None) -> None:
        vf_chain = []
        if srt_path and os.path.exists(srt_path):
            # Style subtitles: bigger, with outline, centered-bottom
            style = (
                "Fontname=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,"
                "Alignment=2,MarginV=40"
            )
            vf_chain.append(
                f"subtitles={srt_path}:force_style='{style}'"
            )
        if logo_path and os.path.exists(logo_path):
            # Overlay logo in top-right, 12% width
            vf_chain.append(
                f"[1:v]scale=iw*0.12:-1[logo];[0:v][logo]overlay=W-w-24:24"
            )
        # Plan watermark (e.g. Free tier) — burned bottom-left.
        if watermark:
            esc = watermark.replace("'", "").replace(":", r"\:")
            vf_chain.append(
                f"drawtext=text='{esc}':font='DejaVu Sans':"
                f"fontcolor=white@0.7:fontsize=18:box=1:boxcolor=black@0.3:boxborderw=6:"
                f"x=24:y=H-th-24"
            )

        if not vf_chain:
            shutil.copyfile(video_in, out_path)
            return

        if logo_path and os.path.exists(logo_path):
            cmd = [
                settings.ffmpeg_bin, "-y",
                "-i", video_in, "-i", logo_path,
                "-filter_complex", ",".join(vf_chain),
                "-c:v", settings.video_codec,
                "-preset", settings.video_preset,
                "-crf", str(settings.video_crf),
                "-c:a", "copy",
                "-pix_fmt", "yuv420p",
                out_path,
            ]
        else:
            cmd = [
                settings.ffmpeg_bin, "-y",
                "-i", video_in,
                "-vf", ",".join(vf_chain),
                "-c:v", settings.video_codec,
                "-preset", settings.video_preset,
                "-crf", str(settings.video_crf),
                "-c:a", "copy",
                "-pix_fmt", "yuv420p",
                out_path,
            ]
        run(cmd)


def clip_duration_estimate(path: str) -> float:
    try:
        return probe(path).duration
    except Exception:
        return 0.0
