"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Palette, Plus, Upload, Trash2, Check, Star, Globe, Type,
  MessageSquare, Loader2, Pencil, Camera,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, BrandKit, mediaUrl } from "@/lib/api";

export default function BrandKitPage() {
  const [kits, setKits] = useState<BrandKit[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<BrandKit | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setKits(await api.brandKits.list()); }
    catch (e) { toast.error("Failed to load brand kits"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const makeDefault = async (kit: BrandKit) => {
    try {
      const updated = await api.brandKits.update(kit.id, { ...kit, is_default: true });
      setKits((ks) => ks.map((k) => ({ ...k, is_default: k.id === kit.id })));
      toast.success(`${kit.name} set as default`);
      void updated;
    } catch (e) { toast.error("Could not set default"); }
  };

  const remove = async (kit: BrandKit) => {
    if (!confirm(`Delete brand kit "${kit.name}"?`)) return;
    try { await api.brandKits.remove(kit.id); setKits((ks) => ks.filter((k) => k.id !== kit.id)); toast.success("Deleted"); }
    catch (e) { toast.error("Delete failed"); }
  };

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><Palette className="size-7" /> Brand Kit</h1>
          <p className="text-ink-400 mt-1">Your default kit is applied automatically to every new render.</p>
        </div>
        <button onClick={() => { setEditing(null); setCreating(true); }} className="btn-primary inline-flex items-center gap-2">
          <Plus className="size-4" /> New Brand Kit
        </button>
      </div>

      {kits.length === 0 && !creating ? (
        <div className="card glass p-12 text-center space-y-3">
          <Palette className="size-8 mx-auto text-ink-500" />
          <p className="text-ink-300">No brand kits yet. Create one to keep colors, fonts and logo consistent.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {kits.map((k) => (
            <KitCard key={k.id} kit={k} onDefault={() => makeDefault(k)} onDelete={() => remove(k)} onEdit={() => { setEditing(k); setCreating(true); }} />
          ))}
        </div>
      )}

      {creating && <EditorModal kit={editing} onClose={() => setCreating(false)} onSaved={async () => { setCreating(false); await load(); }} />}
    </div>
  );
}

function KitCard({ kit, onDefault, onDelete, onEdit }: any) {
  const logo = kit.logo_path ? mediaUrl(kit.logo_path) : null;
  const swatches = [kit.primary_color, kit.secondary_color, kit.accent_color].filter(Boolean) as string[];
  return (
    <div className="card glass p-5 space-y-4">
      <div className="flex items-start gap-4">
        <div className="size-14 rounded-xl bg-ink-900 grid place-items-center overflow-hidden border border-ink-800 shrink-0">
          {logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={logo} alt="logo" className="w-full h-full object-contain" />
          ) : (
            <Camera className="size-5 text-ink-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold truncate">{kit.name}</h3>
            {kit.is_default && <span className="chip chip-active"><Star className="size-3" /> Default</span>}
          </div>
          {kit.description && <p className="text-xs text-ink-400 truncate">{kit.description}</p>}
        </div>
      </div>

      {swatches.length > 0 && (
        <div className="flex gap-2">
          {swatches.map((c, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs text-ink-300">
              <span className="size-5 rounded-md border border-white/10" style={{ background: c }} />
              <span className="font-mono">{c}</span>
            </div>
          ))}
        </div>
      )}

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <Meta icon={<Type className="size-3.5" />} label="Font" value={kit.font_family || "—"} />
        <Meta icon={<Globe className="size-3.5" />} label="Website" value={kit.website || "—"} />
        <Meta icon={<MessageSquare className="size-3.5" />} label="Voice" value={kit.brand_voice || "—"} span />
      </dl>

      <div className="flex items-center gap-2 pt-1">
        {!kit.is_default && <button onClick={onDefault} className="btn-ghost text-amber-300 hover:bg-amber-500/15 flex items-center gap-1.5"><Star className="size-4" /> Set default</button>}
        <button onClick={onEdit} className="icon-btn" title="Edit"><Pencil className="size-4" /></button>
        <button onClick={onDelete} className="icon-btn hover:bg-red-500/20 hover:text-red-300 ml-auto" title="Delete"><Trash2 className="size-4" /></button>
      </div>
    </div>
  );
}

function Meta({ icon, label, value, span }: any) {
  return (
    <div className={`flex items-center gap-2 ${span ? "col-span-2" : ""}`}>
      <span className="text-ink-500">{icon}</span>
      <span className="text-ink-400">{label}:</span>
      <span className="text-ink-100 truncate">{value}</span>
    </div>
  );
}

function EditorModal({ kit, onClose, onSaved }: any) {
  const [form, setForm] = useState({
    name: kit?.name ?? "",
    description: kit?.description ?? "",
    primary_color: kit?.primary_color ?? "#6C5CE7",
    secondary_color: kit?.secondary_color ?? "#A29BFE",
    accent_color: kit?.accent_color ?? "#00CEC9",
    font_family: kit?.font_family ?? "Inter",
    website: kit?.website ?? "",
    brand_voice: kit?.brand_voice ?? "",
    is_default: kit?.is_default ?? false,
  });
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) return toast.error("Name is required");
    setSaving(true);
    try {
      let saved: BrandKit;
      if (kit) saved = await api.brandKits.update(kit.id, form);
      else saved = await api.brandKits.create(form);

      if (logoFile) {
        saved = await api.brandKits.uploadLogo(saved.id, logoFile);
        toast.success("Logo uploaded");
      }
      toast.success(kit ? "Brand kit updated" : "Brand kit created");
      onSaved();
    } catch (e) { toast.error("Save failed"); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={onClose}>
      <div className="card glass w-full max-w-2xl p-5 space-y-4 max-h-[90vh] overflow-y-auto scrollbar-thin" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{kit ? "Edit" : "New"} Brand Kit</h3>
          <button onClick={onClose} className="text-ink-400 hover:text-white">✕</button>
        </div>

        <Field label="Name">
          <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Acme Co." />
        </Field>

        <LivePreview form={form} logoUrl={kit?.logo_path} />

        <div className="grid grid-cols-3 gap-3">
          <ColorField label="Primary" value={form.primary_color} onChange={(v: string) => set("primary_color", v)} />
          <ColorField label="Secondary" value={form.secondary_color} onChange={(v: string) => set("secondary_color", v)} />
          <ColorField label="Accent" value={form.accent_color} onChange={(v: string) => set("accent_color", v)} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Font family">
            <input className="input" value={form.font_family} onChange={(e) => set("font_family", e.target.value)} placeholder="Inter" />
          </Field>
          <Field label="Website">
            <input className="input" value={form.website} onChange={(e) => set("website", e.target.value)} placeholder="https://acme.com" />
          </Field>
        </div>

        <Field label="Brand voice / tone">
          <textarea className="input" rows={2} value={form.brand_voice} onChange={(e) => set("brand_voice", e.target.value)} placeholder="Confident, playful, concise" />
        </Field>

        <Field label="Description">
          <textarea className="input" rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} />
        </Field>

        <Field label="Logo (PNG/JPG/WEBP)">
          <label className="flex items-center justify-center gap-2 border border-dashed border-ink-700 rounded-lg py-4 cursor-pointer hover:bg-ink-800/40 transition">
            <Upload className="size-4" /> {logoFile ? logoFile.name : (kit?.logo_path ? "Replace logo" : "Upload logo")}
            <input type="file" accept="image/*" className="hidden" onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)} />
          </label>
        </Field>

        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={form.is_default} onChange={(e) => set("is_default", e.target.checked)} className="size-4 accent-brand-500" />
          Set as default (used automatically in new renders)
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={submit} disabled={saving} className="btn-primary inline-flex items-center gap-2">
            {saving && <Loader2 className="size-4 animate-spin" />} {kit ? "Save" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

function LivePreview({ form, logoUrl }: any) {
  const logo = logoUrl ? mediaUrl(logoUrl) : null;
  return (
    <div className="rounded-xl border border-ink-800 overflow-hidden" style={{ background: form.primary_color || "#000" }}>
      <div className="p-4 flex items-center gap-3" style={{ background: "rgba(0,0,0,0.25)" }}>
        {logo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={logo} alt="logo" className="size-8 object-contain" />
        ) : (
          <span className="size-8 rounded-lg grid place-items-center text-white font-bold" style={{ background: form.accent_color }}>A</span>
        )}
        <span className="font-semibold text-white">{form.name || "Brand name"}</span>
      </div>
      <div className="p-4 grid grid-cols-3 gap-2" style={{ background: form.secondary_color || "#111" }}>
        <div className="h-10 rounded" style={{ background: form.primary_color }} />
        <div className="h-10 rounded" style={{ background: form.secondary_color }} />
        <div className="h-10 rounded" style={{ background: form.accent_color }} />
      </div>
      <div className="p-4" style={{ background: "rgba(0,0,0,0.35)" }}>
        <p className="text-white/90 text-sm" style={{ fontFamily: form.font_family }}>The quick brown fox jumps over the lazy dog.</p>
        {form.brand_voice && <p className="text-white/60 text-xs mt-1">Voice: {form.brand_voice}</p>}
      </div>
    </div>
  );
}

function Field({ label, children }: any) {
  return (
    <label className="block space-y-1.5">
      <span className="label">{label}</span>
      {children}
    </label>
  );
}

function ColorField({ label, value, onChange }: any) {
  return (
    <label className="space-y-1.5">
      <span className="label">{label}</span>
      <div className="flex items-center gap-2">
        <input type="color" value={value} onChange={(e) => onChange(e.target.value)} className="size-9 rounded-lg bg-transparent border border-ink-700 cursor-pointer" />
        <input className="input font-mono" value={value} onChange={(e) => onChange(e.target.value)} />
      </div>
    </label>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
