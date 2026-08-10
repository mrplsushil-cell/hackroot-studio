import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  const u = ["B", "KB", "MB", "GB"];
  let n = bytes, i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n < 10 ? 1 : 0)} ${u[i]}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch { return iso; }
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

export function statusColor(status: string): string {
  switch (status) {
    case "completed": return "text-emerald-300 bg-emerald-500/10 border-emerald-500/30";
    case "processing": return "text-amber-300 bg-amber-500/10 border-amber-500/30";
    case "queued": return "text-sky-300 bg-sky-500/10 border-sky-500/30";
    case "failed": return "text-rose-300 bg-rose-500/10 border-rose-500/30";
    case "cancelled": return "text-ink-300 bg-ink-700/30 border-ink-600/40";
    default: return "text-ink-300 bg-ink-700/30 border-ink-600/40";
  }
}
