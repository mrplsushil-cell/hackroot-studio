"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCheck, Loader2, Video, CreditCard, AlertTriangle, Wrench } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";

const ICONS: Record<string, any> = {
  video_ready: Video, subscription_activated: CreditCard,
  subscription_expiring: AlertTriangle, payment_failed: AlertTriangle,
  maintenance: Wrench, credits_low: CreditCard,
};

function date(d: string) { return new Date(d).toLocaleString("en-IN"); }

export default function NotificationsPage() {
  const [notes, setNotes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try { setNotes(await api.billing.notifications()); }
    catch { toast.error("Failed to load notifications"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const markRead = async (id: number) => {
    await api.billing.markRead(id).catch(() => {});
    setNotes((ns) => ns.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2"><Bell className="size-7" /> Notifications</h1>
        <button onClick={async () => { await api.billing.markAllRead().catch(() => {}); setNotes((ns) => ns.map((n) => ({ ...n, read: true }))); }} className="btn-ghost inline-flex items-center gap-1.5">
          <CheckCheck className="size-4" /> Mark all read
        </button>
      </div>

      {notes.length === 0 ? (
        <div className="card glass p-10 text-center text-ink-400">You're all caught up.</div>
      ) : (
        <div className="space-y-2">
          {notes.map((n) => {
            const Icon = ICONS[n.type] || Bell;
            return (
              <button key={n.id} onClick={() => markRead(n.id)}
                className={`card glass w-full text-left p-4 flex gap-3 ${n.read ? "opacity-60" : ""}`}>
                <div className="size-9 rounded-lg bg-ink-900 grid place-items-center shrink-0">
                  <Icon className="size-4 text-brand-300" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{n.title}</p>
                  {n.body && <p className="text-sm text-ink-400">{n.body}</p>}
                  <p className="text-xs text-ink-500 mt-1">{date(n.created_at)}</p>
                </div>
                {!n.read && <span className="size-2 rounded-full bg-brand-400 mt-2" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
