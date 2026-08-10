"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Settings as SettingsIcon, Cpu, HardDrive, SlidersHorizontal, CheckCircle2,
  AlertTriangle, KeyRound, Loader2, Boxes,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, ProviderInfo } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  llm: "LLM", image: "Image", video: "Video", tts: "TTS", music: "Music",
};

export default function SettingsPage() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, s] = await Promise.all([api.providers.list(), api.settings.get()]);
      setProviders(p); setConfig(s);
    } catch (e) { toast.error("Failed to load settings"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;
  if (!config) return <Centered><AlertTriangle className="size-6" /> Could not load configuration.</Centered>;

  const allOk = providers.every((p) => p.available);

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2"><SettingsIcon className="size-7" /> Settings</h1>
        <p className="text-ink-400 mt-1">Provider connections and rendering defaults for this deployment.</p>
      </div>

      {/* Environment validation summary */}
      <div className={`card glass p-4 flex items-center gap-3 ${allOk ? "border-emerald-500/30" : "border-amber-500/30"}`}>
        {allOk ? <CheckCircle2 className="size-5 text-emerald-400" /> : <AlertTriangle className="size-5 text-amber-400" />}
        <div className="flex-1">
          <p className="font-medium">{allOk ? "All providers configured" : "Some providers need API keys"}</p>
          <p className="text-xs text-ink-400">
            {allOk ? "Every pipeline stage can run end-to-end." : "Mock providers fall back automatically where keys are missing."}
          </p>
        </div>
      </div>

      {/* API Provider Management */}
      <Section icon={<KeyRound className="size-4" />} title="API Provider Management">
        <div className="space-y-2">
          {providers.map((p) => (
            <div key={p.role} className="flex items-center gap-3 p-3 rounded-lg bg-ink-900/50 border border-ink-800/70">
              <span className="chip chip-active w-20 justify-center">{ROLE_LABEL[p.role] ?? p.role}</span>
              <div className="flex-1 min-w-0">
                <p className="font-medium capitalize">{p.provider} {p.model && <span className="text-ink-400 text-xs">· {p.model}</span>}</p>
                <p className="text-xs truncate">{p.message || (p.available ? "Available" : "Unavailable")}</p>
              </div>
              <StatusDot ok={p.available} />
            </div>
          ))}
        </div>
      </Section>

      {/* Rendering defaults */}
      <Section icon={<SlidersHorizontal className="size-4" />} title="Rendering Defaults">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <KV label="Encoder" value={config.rendering.ffmpeg_bin} />
          <KV label="Preset" value={config.rendering.video_preset} />
          <KV label="CRF" value={String(config.rendering.video_crf)} />
          <KV label="Audio codec" value={config.rendering.audio_codec} />
          <KV label="Audio bitrate" value={config.rendering.audio_bitrate} />
          <KV label="Probe" value={config.rendering.ffprobe_bin} />
        </div>
      </Section>

      {/* Storage settings */}
      <Section icon={<HardDrive className="size-4" />} title="Storage Settings">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <KV label="Backend" value={config.storage.backend} />
          <KV label="Max upload" value={`${config.storage.max_upload_size_mb} MB`} />
          <KV label="Local root" value={config.storage.local_root} mono />
          <KV label="Public base URL" value={config.storage.public_base_url} mono />
        </div>
      </Section>

      {/* Auth */}
      <Section icon={<Boxes className="size-4" />} title="Auth">
        <div className="grid grid-cols-2 gap-3">
          <KV label="JWT algorithm" value={config.auth.jwt_algorithm} />
          <KV label="Token lifetime" value={`${config.auth.jwt_expires_minutes} min`} />
        </div>
      </Section>
    </div>
  );
}

function Section({ icon, title, children }: any) {
  return (
    <section className="card glass p-5 space-y-3">
      <h2 className="font-semibold flex items-center gap-2 text-ink-100">{icon}{title}</h2>
      {children}
    </section>
  );
}

function KV({ label, value, mono }: any) {
  return (
    <div className="p-3 rounded-lg bg-ink-900/50 border border-ink-800/70">
      <p className="label">{label}</p>
      <p className={`text-sm text-ink-100 break-all ${mono ? "font-mono text-xs" : ""}`}>{value}</p>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`size-2.5 rounded-full ${ok ? "bg-emerald-400" : "bg-amber-400"}`} title={ok ? "OK" : "Needs key"} />
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
