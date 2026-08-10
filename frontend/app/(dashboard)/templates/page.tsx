"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  LayoutTemplate, Plus, Sparkles, ShoppingBag, Rocket, Instagram, Youtube,
  Building2, Tag, BookOpen, Play, Loader2, Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, Template } from "@/lib/api";

const ICONS: Record<string, any> = {
  "shopping-bag": ShoppingBag, "rocket": Rocket, "instagram": Instagram, "youtube": Youtube,
  "building": Building2, "tag": Tag, "book": BookOpen, "sparkles": Sparkles,
};

const CATEGORIES = ["All", "Marketing", "Fashion", "Social", "Corporate", "Branding", "Custom"];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [cat, setCat] = useState("All");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setTemplates(await api.templates.list()); }
    catch (e) { toast.error("Failed to load templates"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(
    () => cat === "All" ? templates : templates.filter((t) => t.category === cat),
    [templates, cat]
  );

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><LayoutTemplate className="size-7" /> Templates</h1>
          <p className="text-ink-400 mt-1">Start from a proven structure, then customise in the editor.</p>
        </div>
        <button onClick={() => setCreating(true)} className="btn-primary inline-flex items-center gap-2">
          <Plus className="size-4" /> Custom Template
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => setCat(c)}
            className={`chip ${cat === c ? "chip-active" : ""}`}>{c}</button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((t) => <TemplateCard key={t.id} t={t} />)}
      </div>

      {creating && <CreateModal onClose={() => setCreating(false)} onSaved={async () => { setCreating(false); await load(); }} />}
    </div>
  );
}

function TemplateCard({ t }: { t: Template }) {
  const Icon = ICONS[t.icon || "sparkles"] || Sparkles;
  let scenes: any[] = [];
  try { scenes = JSON.parse(t.scene_blueprint || "[]"); } catch { /* ignore */ }
  const summary: Record<string, any> = {};
  scenes.forEach((s) => { const b = (s.beat || s.label || "Scene"); summary[b] = (summary[b] || 0) + 1; });
  const beats = Object.keys(summary);

  return (
    <div className="card glass overflow-hidden group">
      <div className="aspect-video bg-gradient-to-br from-brand-500/20 to-accent-500/10 grid place-items-center relative">
        <Icon className="size-10 text-white/80" />
        <span className="absolute top-2 left-2 chip text-[10px]">{t.category}</span>
        {!t.is_system && <span className="absolute top-2 right-2 chip chip-active text-[10px]">Custom</span>}
      </div>
      <div className="p-4 space-y-3">
        <div>
          <h3 className="font-semibold">{t.name}</h3>
          {t.description && <p className="text-xs text-ink-400 line-clamp-2">{t.description}</p>}
        </div>
        <div className="flex flex-wrap gap-1.5 text-[11px] text-ink-300">
          <span className="chip">{t.default_duration}s</span>
          <span className="chip">{t.default_aspect_ratio}</span>
          <span className="chip">{t.default_voice}</span>
          <span className="chip">{t.default_language}</span>
        </div>
        {beats.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {beats.map((b) => <span key={b} className="text-[10px] px-1.5 py-0.5 rounded bg-ink-800/70 text-ink-300">{b}</span>)}
          </div>
        )}
        <Link href={`/create?template=${t.id}`} className="btn-primary w-full justify-center inline-flex items-center gap-2">
          <Play className="size-4" /> Use template
        </Link>
      </div>
    </div>
  );
}

function CreateModal({ onClose, onSaved }: any) {
  const [form, setForm] = useState({
    name: "", description: "", category: "Custom",
    default_duration: 15, default_aspect_ratio: "9:16", default_style: "Cinematic",
    default_voice: "female", default_language: "English",
    cta_template: "Order now", caption_style: "bold-center",
    scene_blueprint: JSON.stringify(
      [{ beat: "Hook" }, { beat: "Showcase" }, { beat: "Call to Action" }], null, 2
    ),
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) return toast.error("Name is required");
    try { JSON.parse(form.scene_blueprint); } catch { return toast.error("Scene blueprint must be valid JSON"); }
    setSaving(true);
    try {
      await api.templates.create(form);
      toast.success("Custom template created");
      onSaved();
    } catch (e) { toast.error("Create failed"); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={onClose}>
      <div className="card glass w-full max-w-xl p-5 space-y-4 max-h-[90vh] overflow-y-auto scrollbar-thin" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Custom Template</h3>
          <button onClick={onClose} className="text-ink-400 hover:text-white">✕</button>
        </div>
        <input className="input" placeholder="Template name" value={form.name} onChange={(e) => set("name", e.target.value)} />
        <textarea className="input" rows={2} placeholder="Description" value={form.description} onChange={(e) => set("description", e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <label className="space-y-1.5"><span className="label">Duration (s)</span>
            <input type="number" className="input" value={form.default_duration} onChange={(e) => set("default_duration", +e.target.value)} /></label>
          <label className="space-y-1.5"><span className="label">Aspect</span>
            <select className="input" value={form.default_aspect_ratio} onChange={(e) => set("default_aspect_ratio", e.target.value)}>
              {["9:16", "16:9", "1:1", "4:5"].map((a) => <option key={a}>{a}</option>)}
            </select></label>
        </div>
        <label className="space-y-1.5"><span className="label">Scene blueprint (JSON array of beats)</span>
          <textarea className="input font-mono text-xs" rows={6} value={form.scene_blueprint}
            onChange={(e) => set("scene_blueprint", e.target.value)} /></label>
        <label className="space-y-1.5"><span className="label">CTA text</span>
          <input className="input" value={form.cta_template} onChange={(e) => set("cta_template", e.target.value)} /></label>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={submit} disabled={saving} className="btn-primary inline-flex items-center gap-2">
            {saving && <Loader2 className="size-4 animate-spin" />} Create
          </button>
        </div>
      </div>
    </div>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
