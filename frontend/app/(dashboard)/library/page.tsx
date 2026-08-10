"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  LayoutGrid, List, Search, Play, Pencil, Copy, Trash2, Download,
  Plus, Loader2, AlertTriangle, Filter, ChevronLeft, ChevronRight,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, VideoSummary, mediaUrl } from "@/lib/api";

type ViewMode = "grid" | "list";
type Status = "draft" | "queued" | "processing" | "completed" | "failed" | "cancelled";

const STATUS_STYLES: Record<Status, string> = {
  draft: "bg-ink-700 text-ink-200",
  queued: "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30",
  processing: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  completed: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  failed: "bg-red-500/20 text-red-300 border border-red-500/30",
  cancelled: "bg-ink-700 text-ink-300",
};

const PAGE_SIZE = 9;

export default function LibraryPage() {
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("grid");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status | "all">("all");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [preview, setPreview] = useState<VideoSummary | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.videos.listVideos(200, 0);
      setVideos(data);
      setTotal(data.length);
    } catch (e) {
      toast.error("Failed to load videos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Apply client-side filter + search (server returns all owned videos).
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return videos.filter((v) => {
      if (status !== "all" && v.status !== status) return false;
      if (q && !v.title.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [videos, query, status]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const paged = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  const remove = async (id: number) => {
    if (!confirm("Delete this video? This cannot be undone.")) return;
    try {
      await api.videos.remove(id);
      toast.success("Deleted");
      setVideos((vs) => vs.filter((v) => v.id !== id));
      setTotal((t) => t - 1);
      if (preview?.id === id) setPreview(null);
    } catch (e) { toast.error("Delete failed"); }
  };

  const duplicate = async (id: number) => {
    try {
      const v = await api.videos.duplicate(id);
      toast.success("Duplicated");
      await load();
      setPreview(v as unknown as VideoSummary);
    } catch (e) { toast.error("Duplicate failed"); }
  };

  const rename = async (v: VideoSummary) => {
    const title = prompt("New title:", v.title);
    if (!title || title === v.title) return;
    try {
      await api.videos.rename(v.id, title);
      toast.success("Renamed");
      setVideos((vs) => vs.map((x) => (x.id === v.id ? { ...x, title } : x)));
    } catch (e) { toast.error("Rename failed"); }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold">My Videos</h1>
          <p className="text-ink-400 mt-1">{total} video{total === 1 ? "" : "s"} in your library</p>
        </div>
        <Link href="/create" className="btn-primary inline-flex items-center gap-2">
          <Plus className="size-4" /> New Video
        </Link>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-ink-500" />
          <input
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(0); }}
            placeholder="Search by title…"
            className="input pl-9 w-full"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-ink-500" />
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value as Status | "all"); setPage(0); }}
            className="input pl-9 pr-8 appearance-none"
          >
            <option value="all">All statuses</option>
            <option value="draft">Draft</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="flex rounded-lg border border-ink-800 overflow-hidden">
          <button
            onClick={() => setView("grid")}
            className={view === "grid" ? "bg-brand-500/20 text-white p-2" : "text-ink-400 p-2 hover:bg-ink-800/50"}
            aria-label="Grid view"
          ><LayoutGrid className="size-4" /></button>
          <button
            onClick={() => setView("list")}
            className={view === "list" ? "bg-brand-500/20 text-white p-2" : "text-ink-400 p-2 hover:bg-ink-800/50"}
            aria-label="List view"
          ><List className="size-4" /></button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid place-items-center py-20 text-ink-400"><Loader2 className="size-6 animate-spin" /></div>
      ) : paged.length === 0 ? (
        <div className="card glass p-12 text-center space-y-3">
          <AlertTriangle className="size-8 mx-auto text-ink-500" />
          <p className="text-ink-300">No videos match your filters.</p>
          <Link href="/create" className="btn-primary inline-flex items-center gap-2"><Plus className="size-4" /> Create your first video</Link>
        </div>
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {paged.map((v) => (
            <VideoCard key={v.id} v={v} onPreview={() => setPreview(v)}
              onRename={() => rename(v)} onDuplicate={() => duplicate(v.id)} onDelete={() => remove(v.id)} />
          ))}
        </div>
      ) : (
        <div className="card glass divide-y divide-ink-800/70">
          {paged.map((v) => <VideoRow key={v.id} v={v} onPreview={() => setPreview(v)}
            onRename={() => rename(v)} onDuplicate={() => duplicate(v.id)} onDelete={() => remove(v.id)} />)}
        </div>
      )}

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}
            className="btn-ghost p-2 disabled:opacity-40"><ChevronLeft className="size-4" /></button>
          <span className="text-sm text-ink-400">Page {safePage + 1} of {pageCount}</span>
          <button disabled={safePage >= pageCount - 1} onClick={() => setPage(safePage + 1)}
            className="btn-ghost p-2 disabled:opacity-40"><ChevronRight className="size-4" /></button>
        </div>
      )}

      {preview && <PreviewModal v={preview} onClose={() => setPreview(null)} onDeleted={() => { setPreview(null); load(); }} />}
    </div>
  );
}

function StatusBadge({ s }: { s: Status }) {
  return <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[s]}`}>{s}</span>;
}

function Thumb({ v, className }: { v: VideoSummary; className?: string }) {
  const src = v.thumbnail_path ? mediaUrl(v.thumbnail_path) : null;
  return (
    <div className={`relative bg-ink-900 ${className ?? ""}`}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={v.title} className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full grid place-items-center text-ink-600 text-xs">No preview</div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
    </div>
  );
}

function VideoCard({ v, onPreview, onRename, onDuplicate, onDelete }: any) {
  return (
    <div className="card glass overflow-hidden group">
      <button onClick={onPreview} className="block w-full aspect-video relative">
        <Thumb v={v} className="w-full h-full" />
        <span className="absolute inset-0 grid place-items-center opacity-0 group-hover:opacity-100 transition bg-black/40">
          <span className="size-12 rounded-full bg-white/90 grid place-items-center text-ink-950"><Play className="size-5" /></span>
        </span>
      </button>
      <div className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="font-medium truncate" title={v.title}>{v.title}</p>
          <StatusBadge s={v.status as Status} />
        </div>
        <p className="text-xs text-ink-400">{v.duration}s · {v.aspect_ratio}</p>
        <div className="flex items-center gap-1 pt-1">
          <IconBtn onClick={onPreview} title="Preview"><Play className="size-4" /></IconBtn>
          <IconBtn onClick={onRename} title="Rename"><Pencil className="size-4" /></IconBtn>
          <IconBtn onClick={onDuplicate} title="Duplicate"><Copy className="size-4" /></IconBtn>
          <a href={api.videos.downloadUrl(v.id)} className="icon-btn" title="Download" onClick={(e) => { if (v.status !== "completed") e.preventDefault(); }}><Download className="size-4" /></a>
          <IconBtn onClick={onDelete} title="Delete" danger><Trash2 className="size-4" /></IconBtn>
        </div>
      </div>
    </div>
  );
}

function VideoRow({ v, onPreview, onRename, onDuplicate, onDelete }: any) {
  return (
    <div className="flex items-center gap-4 p-3 hover:bg-ink-800/30">
      <button onClick={onPreview} className="shrink-0"><Thumb v={v} className="w-28 aspect-video rounded-md overflow-hidden" /></button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium truncate">{v.title}</p>
          <StatusBadge s={v.status as Status} />
        </div>
        <p className="text-xs text-ink-400">{v.duration}s · {v.aspect_ratio} · {new Date(v.created_at).toLocaleDateString()}</p>
      </div>
      <div className="flex items-center gap-1">
        <IconBtn onClick={onPreview} title="Preview"><Play className="size-4" /></IconBtn>
        <IconBtn onClick={onRename} title="Rename"><Pencil className="size-4" /></IconBtn>
        <IconBtn onClick={onDuplicate} title="Duplicate"><Copy className="size-4" /></IconBtn>
        <a href={api.videos.downloadUrl(v.id)} className="icon-btn" title="Download"><Download className="size-4" /></a>
        <IconBtn onClick={onDelete} title="Delete" danger><Trash2 className="size-4" /></IconBtn>
      </div>
    </div>
  );
}

function IconBtn({ children, onClick, title, danger }: any) {
  return (
    <button onClick={onClick} title={title}
      className={`icon-btn ${danger ? "hover:bg-red-500/20 hover:text-red-300" : "hover:bg-brand-500/20 hover:text-white"}`}>
      {children}
    </button>
  );
}

function PreviewModal({ v, onClose, onDeleted }: any) {
  const [playing, setPlaying] = useState(false);
  const done = v.status === "completed";
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={onClose}>
      <div className="card glass w-full max-w-2xl p-4 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold truncate">{v.title}</h3>
            <StatusBadge s={v.status as Status} />
          </div>
          <button onClick={onClose} className="text-ink-400 hover:text-white">✕</button>
        </div>
        <div className="aspect-video bg-black rounded-lg overflow-hidden grid place-items-center">
          {done ? (
            playing ? (
              <video src={api.videos.downloadUrl(v.id)} controls autoPlay className="w-full h-full" />
            ) : (
              <button onClick={() => setPlaying(true)} className="grid place-items-center gap-2 text-white">
                <span className="size-16 rounded-full bg-white/90 text-ink-950 grid place-items-center"><Play className="size-7" /></span>
                <span className="text-sm text-ink-300">Play video</span>
              </button>
            )
          ) : (
            <p className="text-ink-400 text-sm px-6 text-center">
              {v.status === "failed" ? "Generation failed — regenerate from Create." : "Video is not ready yet."}
            </p>
          )}
        </div>
        <div className="flex items-center justify-between text-sm text-ink-400">
          <span>{v.duration}s · {v.aspect_ratio}</span>
          <div className="flex gap-2">
            <button onClick={onDeleted} className="btn-ghost text-red-300 hover:bg-red-500/20">Delete</button>
            <a href={api.videos.downloadUrl(v.id)} className={`btn-primary ${done ? "" : "pointer-events-none opacity-40"}`}>Download</a>
          </div>
        </div>
      </div>
    </div>
  );
}
