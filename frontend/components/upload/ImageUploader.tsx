"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { Asset, UploadLimits, api, formatBytes } from "@/lib/api";

const FALLBACK_LIMITS: UploadLimits = {
  max_file_size_bytes: 20 * 1024 * 1024,
  max_file_size_mb: 20,
  max_images_per_project: 20,
  allowed_mime_types: ["image/jpeg", "image/png", "image/webp"],
  allowed_extensions: [".jpg", ".jpeg", ".png", ".webp"],
  compression: "none",
};

const ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

export type ImageUploaderProps = {
  /** Attach uploads to a specific project. Omit for the standalone asset library. */
  videoId?: number;
  /** Called whenever the asset list changes (upload, delete, reorder). */
  onChange?: (assets: Asset[]) => void;
  className?: string;
};

type Pending = { id: string; name: string; progress: number };

/**
 * Image upload + asset manager.
 *
 * Enforces the same contract as the API (JPG/JPEG/PNG/WEBP, 20 MB, 20 per
 * project) client-side for fast feedback, but the server remains authoritative.
 * Images are never compressed — the exact bytes the user picked are uploaded.
 */
export function ImageUploader({ videoId, onChange, className = "" }: ImageUploaderProps) {
  const [limits, setLimits] = useState<UploadLimits>(FALLBACK_LIMITS);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [loading, setLoading] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const publish = useCallback(
    (next: Asset[]) => {
      setAssets(next);
      onChange?.(next);
    },
    [onChange]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [l, a] = await Promise.all([
          api.assets.limits().catch(() => FALLBACK_LIMITS),
          api.assets.list({ video_id: videoId, kind: "image" }).catch(() => [] as Asset[]),
        ]);
        if (cancelled) return;
        setLimits(l);
        setAssets(a);
        onChange?.(a);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  const validateLocally = (file: File, alreadyQueued: number): string | null => {
    const ext = `.${(file.name.split(".").pop() || "").toLowerCase()}`;
    if (!limits.allowed_extensions.includes(ext)) {
      return `${file.name}: only ${limits.allowed_extensions.join(", ")} are allowed`;
    }
    const type = file.type === "image/jpg" ? "image/jpeg" : file.type;
    if (type && !limits.allowed_mime_types.includes(type)) {
      return `${file.name}: unsupported file type "${file.type}"`;
    }
    if (file.size > limits.max_file_size_bytes) {
      return `${file.name}: ${formatBytes(file.size)} exceeds the ${limits.max_file_size_mb} MB limit`;
    }
    if (assets.length + alreadyQueued >= limits.max_images_per_project) {
      return `Limit reached — a project can hold at most ${limits.max_images_per_project} images`;
    }
    return null;
  };

  const handleFiles = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (!files.length) return;

    const accepted: File[] = [];
    files.forEach((f) => {
      const err = validateLocally(f, accepted.length);
      if (err) toast.error(err);
      else accepted.push(f);
    });
    if (!accepted.length) return;

    const uploaded: Asset[] = [];
    for (const file of accepted) {
      const key = `${file.name}-${file.size}-${Math.random().toString(36).slice(2)}`;
      setPending((p) => [...p, { id: key, name: file.name, progress: 0 }]);
      try {
        const asset = await api.assets.upload(file, {
          videoId,
          onProgress: (pct) =>
            setPending((p) => p.map((x) => (x.id === key ? { ...x, progress: pct } : x))),
        });
        uploaded.push(asset);
      } catch {
        /* interceptor already surfaced the error toast */
      } finally {
        setPending((p) => p.filter((x) => x.id !== key));
      }
    }
    if (uploaded.length) {
      publish([...assets, ...uploaded]);
      toast.success(`Uploaded ${uploaded.length} image${uploaded.length > 1 ? "s" : ""}`);
    }
  };

  const remove = async (asset: Asset) => {
    const previous = assets;
    publish(assets.filter((a) => a.id !== asset.id));
    try {
      await api.assets.remove(asset.id);
    } catch {
      publish(previous);
    }
  };

  const persistOrder = async (next: Asset[]) => {
    const previous = assets;
    publish(next);
    try {
      await api.assets.reorder(next.map((a) => a.id));
    } catch {
      publish(previous);
    }
  };

  const move = (from: number, to: number) => {
    if (to < 0 || to >= assets.length || from === to) return;
    const next = [...assets];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    void persistOrder(next);
  };

  const remaining = limits.max_images_per_project - assets.length;

  return (
    <div className={className}>
      {/* Dropzone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload images"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files?.length) void handleFiles(e.dataTransfer.files);
        }}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
          dragOver
            ? "border-brand-400 bg-brand-500/10"
            : "border-ink-700 hover:border-ink-500 bg-ink-900/30"
        } ${remaining <= 0 ? "opacity-50 pointer-events-none" : ""}`}
      >
        <div className="text-3xl mb-2">🖼️</div>
        <p className="font-medium">
          {remaining > 0 ? "Drop images here or click to browse" : "Image limit reached"}
        </p>
        <p className="text-xs text-ink-400 mt-1">
          JPG, JPEG, PNG, WEBP · up to {limits.max_file_size_mb} MB each · {assets.length}/
          {limits.max_images_per_project} used · no compression applied
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {/* In-flight uploads */}
      {pending.length > 0 && (
        <ul className="mt-4 space-y-2">
          {pending.map((p) => (
            <li key={p.id} className="rounded-lg bg-ink-900/50 border border-ink-800 p-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="truncate text-ink-300">{p.name}</span>
                <span className="text-ink-400">{p.progress}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-ink-700 overflow-hidden">
                <div className="h-full bg-brand-500 transition-all" style={{ width: `${p.progress}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Previews / manager */}
      {loading ? (
        <p className="mt-4 text-sm text-ink-400">Loading images…</p>
      ) : assets.length > 0 ? (
        <>
          <p className="mt-6 mb-2 text-xs text-ink-400">
            Drag a tile, or use the arrows, to set the order scenes use these images.
          </p>
          <ul className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {assets.map((a, i) => (
              <li
                key={a.id}
                draggable
                onDragStart={() => setDragIndex(i)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (dragIndex !== null) move(dragIndex, i);
                  setDragIndex(null);
                }}
                className="group relative rounded-lg overflow-hidden border border-ink-800 bg-ink-900/60"
              >
                <span className="absolute top-2 left-2 z-10 rounded bg-black/70 px-2 py-0.5 text-[11px] font-semibold">
                  #{i + 1}
                </span>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={api.assets.previewUrl(a.id)}
                  alt={a.original_filename || a.name}
                  className="aspect-square w-full object-cover"
                  loading="lazy"
                />
                <div className="p-2">
                  <p className="truncate text-xs text-ink-200" title={a.original_filename || a.name}>
                    {a.original_filename || a.name}
                  </p>
                  <p className="text-[11px] text-ink-500">
                    {a.width}×{a.height} · {formatBytes(a.file_size_bytes)}
                  </p>
                </div>
                <div className="absolute inset-x-0 bottom-0 flex justify-between gap-1 bg-black/75 p-1 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
                  <button
                    type="button"
                    aria-label="Move left"
                    disabled={i === 0}
                    onClick={() => move(i, i - 1)}
                    className="px-2 text-sm disabled:opacity-30"
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    aria-label="Delete image"
                    onClick={() => void remove(a)}
                    className="px-2 text-sm text-red-400 hover:text-red-300"
                  >
                    Delete
                  </button>
                  <button
                    type="button"
                    aria-label="Move right"
                    disabled={i === assets.length - 1}
                    onClick={() => move(i, i + 1)}
                    className="px-2 text-sm disabled:opacity-30"
                  >
                    →
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}

export default ImageUploader;
