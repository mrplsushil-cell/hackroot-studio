"use client";
import { Bell, Search, LogOut, User as UserIcon, Zap, CreditCard } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export function Topbar() {
  const { user, clear } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [notes, setNotes] = useState<any[]>([]);

  useEffect(() => {
    if (!user) return;
    const load = async () => {
      try {
        setUnread(await api.billing.unreadCount());
        setNotes(await api.billing.notifications());
      } catch { /* ignore */ }
    };
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [user]);

  const onLogout = () => { clear(); router.push("/login"); };

  const openNote = async (n: any) => {
    try { await api.billing.markRead(n.id); } catch { /* */ }
    setUnread((u) => Math.max(0, u - 1));
    if (n.link) router.push(n.link);
    setBellOpen(false);
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-ink-800/80 bg-ink-950/80 px-4 backdrop-blur">
      <div className="flex-1 max-w-2xl">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 size-4 text-ink-400" />
          <input type="text" placeholder="Search videos, templates, assets…" className="input pl-10" />
        </div>
      </div>

      <Link href="/pricing" className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-ink-800/80 bg-ink-900/70 px-3 py-1.5 text-xs hover:border-brand-500/40">
        <CreditCard className="size-3.5 text-brand-300" />
        <span className="text-ink-200">Plans</span>
      </Link>

      <Link href="/billing" className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-ink-800/80 bg-ink-900/70 px-3 py-1.5 text-xs">
        <Zap className="size-3.5 text-amber-300" />
        <span className="text-ink-200">{user ? `${Math.max(0, user.credits_total - user.credits_used)} credits` : "—"}</span>
      </Link>

      <div className="relative">
        <button onClick={() => setBellOpen((v) => !v)} className="rounded-lg p-2 text-ink-300 hover:bg-ink-800/60 hover:text-white" aria-label="Notifications">
          <Bell className="size-4" />
          {unread > 0 && <span className="absolute -top-0.5 -right-0.5 size-4 rounded-full bg-rose-500 text-[10px] font-bold grid place-items-center text-white">{unread > 9 ? "9+" : unread}</span>}
        </button>
        {bellOpen && (
          <div className="absolute right-0 mt-2 w-80 rounded-xl border border-ink-800 bg-ink-900 p-2 shadow-xl max-h-96 overflow-y-auto scrollbar-thin">
            <div className="flex items-center justify-between px-2 py-1.5">
              <span className="text-sm font-semibold">Notifications</span>
              <button onClick={async () => { await api.billing.markAllRead().catch(() => {}); setUnread(0); }} className="text-xs text-brand-300 hover:underline">Mark all read</button>
            </div>
            {notes.length === 0 ? (
              <p className="px-2 py-6 text-center text-xs text-ink-400">No notifications yet.</p>
            ) : (
              notes.map((n) => (
                <button key={n.id} onClick={() => openNote(n)} className={`block w-full text-left rounded-lg px-2 py-2 hover:bg-ink-800/60 ${n.read ? "opacity-60" : ""}`}>
                  <p className="text-sm font-medium">{n.title}</p>
                  {n.body && <p className="text-xs text-ink-400 line-clamp-2">{n.body}</p>}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="relative">
        <button onClick={() => setOpen((v) => !v)} className="flex items-center gap-2 rounded-lg border border-ink-800/80 bg-ink-900/70 px-2.5 py-1.5 hover:bg-ink-800/70">
          <div className="size-7 rounded-full bg-gradient-to-br from-brand-500 to-accent-500 grid place-items-center text-xs font-semibold text-white">
            {user?.email?.[0]?.toUpperCase() || <UserIcon className="size-3.5" />}
          </div>
          <span className="hidden sm:block text-sm text-ink-100 max-w-[10ch] truncate">{user?.full_name || user?.email?.split("@")[0] || "Account"}</span>
        </button>
        {open && (
          <div className="absolute right-0 mt-2 w-56 rounded-xl border border-ink-800 bg-ink-900 p-2 shadow-xl" onMouseLeave={() => setOpen(false)}>
            <div className="px-3 py-2">
              <p className="text-sm font-medium">{user?.email}</p>
              <p className="text-xs text-ink-400">Signed in</p>
            </div>
            <div className="my-1 h-px bg-ink-800" />
            <Link href="/billing" className="block rounded-md px-3 py-2 text-sm hover:bg-ink-800/60">Billing</Link>
            <Link href="/settings" className="block rounded-md px-3 py-2 text-sm hover:bg-ink-800/60">Settings</Link>
            <button onClick={onLogout} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-rose-300 hover:bg-rose-500/10">
              <LogOut className="size-4" /> Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
