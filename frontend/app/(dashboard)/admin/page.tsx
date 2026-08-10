"use client";

import { useEffect, useState } from "react";
import {
  LayoutDashboard, Users, CreditCard, Receipt, LayoutTemplate, Palette,
  Film, ScrollText, ShieldCheck, BarChart3, Loader2, Coins,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";

function inr(p: number) { return "₹" + (p / 100).toLocaleString("en-IN"); }

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "users", label: "Users", icon: Users },
  { id: "subscriptions", label: "Subscriptions", icon: CreditCard },
  { id: "invoices", label: "Invoices", icon: Receipt },
  { id: "templates", label: "Templates", icon: LayoutTemplate },
  { id: "brandkits", label: "Brand Kits", icon: Palette },
  { id: "videos", label: "Videos", icon: Film },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "logs", label: "Request Logs", icon: ScrollText },
  { id: "audit", label: "Audit", icon: ShieldCheck },
];

export default function AdminPage() {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [subs, setSubs] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [brandKits, setBrandKits] = useState<any[]>([]);
  const [videos, setVideos] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, u, sub, inv, t, b, v, a, rl, al] = await Promise.all([
        api.admin.stats(), api.admin.users(), api.admin.subscriptions(),
        api.admin.invoices(), api.admin.templates(), api.admin.brandKits(),
        api.admin.videos(), api.admin.analytics(), api.admin.requestLogs(),
        api.admin.auditLogs(),
      ]);
      setStats(s); setUsers(u); setSubs(sub); setInvoices(inv);
      setTemplates(t); setBrandKits(b); setVideos(v); setAnalytics(a);
      setLogs(rl); setAudit(al);
    } catch (e: any) {
      if (e?.response?.status === 403) toast.error("Admin access required");
      else toast.error("Failed to load admin data");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const adjust = async (uid: number) => {
    const amt = prompt("Adjust credits (+/-):", "10");
    if (!amt) return;
    try {
      await api.admin.adjustCredits(uid, parseInt(amt, 10));
      toast.success("Credits adjusted");
      const u = users.map((x) => x.id === uid ? { ...x, credits_total: x.credits_total + parseInt(amt, 10) } : x);
      setUsers(u);
    } catch { toast.error("Adjust failed"); }
  };

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <h1 className="text-3xl font-bold">Admin</h1>

      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`chip ${tab === t.id ? "chip-active" : ""} inline-flex items-center gap-1.5`}>
              <Icon className="size-3.5" /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === "overview" && stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPI label="Total Users" value={stats.total_users} />
          <KPI label="Active Subs" value={stats.active_subscriptions} />
          <KPI label="Total Videos" value={stats.total_videos} />
          <KPI label="Videos (30d)" value={stats.videos_last_30d} />
          <KPI label="Revenue (30d)" value={inr(stats.revenue_last_30d)} />
          <KPI label="New Users (30d)" value={stats.new_users_last_30d} />
          <KPI label="Credits Used" value={stats.credits_consumed} />
          <KPI label="Failed Payments" value={stats.failed_payments} />
        </div>
      )}

      {tab === "users" && (
        <Table>
          <thead><tr><Th>ID</Th><Th>Email</Th><Th>Name</Th><Th>Credits</Th><Th>Active</Th><Th></Th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <Td>{u.id}</Td><Td>{u.email}</Td><Td>{u.full_name || "—"}</Td>
                <Td>{u.credits_total - u.credits_used} / {u.credits_total}</Td>
                <Td>{u.is_active ? "✓" : "✕"}</Td>
                <Td><button onClick={() => adjust(u.id)} className="icon-btn" title="Adjust credits"><Coins className="size-4" /></button></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {tab === "subscriptions" && (
        <Table>
          <thead><tr><Th>ID</Th><Th>User</Th><Th>Plan</Th><Th>Status</Th><Th>Cycle</Th><Th>Ends</Th></tr></thead>
          <tbody>{subs.map((s) => (
            <tr key={s.id}><Td>{s.id}</Td><Td>{s.user_id}</Td><Td>{s.plan}</Td><Td>{s.status}</Td><Td>{s.billing_cycle}</Td><Td>{s.current_period_end ? new Date(s.current_period_end).toLocaleDateString() : "—"}</Td></tr>
          ))}</tbody>
        </Table>
      )}

      {tab === "invoices" && (
        <Table>
          <thead><tr><Th>Invoice</Th><Th>User</Th><Th>Amount</Th><Th>Status</Th><Th>Date</Th></tr></thead>
          <tbody>{invoices.map((i) => (
            <tr key={i.id}><Td>{i.invoice_no}</Td><Td>{i.user_id}</Td><Td>{inr(i.amount)}</Td><Td>{i.status}</Td><Td>{new Date(i.created_at).toLocaleDateString()}</Td></tr>
          ))}</tbody>
        </Table>
      )}

      {tab === "templates" && (
        <Table>
          <thead><tr><Th>ID</Th><Th>Name</Th><Th>Category</Th><Th>System</Th><Th>Active</Th></tr></thead>
          <tbody>{templates.map((t) => (
            <tr key={t.id}><Td>{t.id}</Td><Td>{t.name}</Td><Td>{t.category}</Td><Td>{t.is_system ? "✓" : "—"}</Td><Td>{t.is_active ? "✓" : "✕"}</Td></tr>
          ))}</tbody>
        </Table>
      )}

      {tab === "brandkits" && (
        <Table>
          <thead><tr><Th>ID</Th><Th>Name</Th><Th>Owner</Th><Th>Default</Th></tr></thead>
          <tbody>{brandKits.map((b) => (
            <tr key={b.id}><Td>{b.id}</Td><Td>{b.name}</Td><Td>{b.owner_id}</Td><Td>{b.is_default ? "✓" : "—"}</Td></tr>
          ))}</tbody>
        </Table>
      )}

      {tab === "videos" && (
        <Table>
          <thead><tr><Th>ID</Th><Th>Owner</Th><Th>Title</Th><Th>Duration</Th><Th>Status</Th></tr></thead>
          <tbody>{videos.map((v) => (
            <tr key={v.id}><Td>{v.id}</Td><Td>{v.owner_id}</Td><Td className="truncate max-w-[200px]">{v.title}</Td><Td>{v.duration}s</Td><Td>{v.status}</Td></tr>
          ))}</tbody>
        </Table>
      )}

      {tab === "analytics" && analytics && (
        <div className="space-y-4">
          <div className="card glass p-4">
            <h3 className="font-semibold mb-2">Daily Revenue (14d)</h3>
            <BarChart data={analytics.daily_revenue.map((d: any) => ({ label: d.date.slice(5), value: d.revenue }))} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ListCard title="Top Plans" items={analytics.top_plans} />
            <ListCard title="Top Templates" items={analytics.top_templates} />
            <ListCard title="Most Active Users" items={analytics.top_users} />
            <div className="card glass p-4"><p className="text-sm text-ink-300">Active users (videos): <b>{analytics.active_users}</b></p></div>
          </div>
        </div>
      )}

      {tab === "logs" && (
        <Table>
          <thead><tr><Th>Method</Th><Th>Path</Th><Th>Status</Th><Th>User</Th><Th>IP</Th><Th>Latency</Th></tr></thead>
          <tbody>{logs.slice(0, 100).map((r) => (
            <tr key={r.id}><Td>{r.method}</Td><Td className="truncate max-w-[240px]">{r.path}</Td><Td>{r.status_code}</Td><Td>{r.user_id ?? "—"}</Td><Td>{r.ip}</Td><Td>{r.latency_ms}ms</Td></tr>
          ))}</tbody>
        </Table>
      )}

      {tab === "audit" && (
        <Table>
          <thead><tr><Th>Action</Th><Th>Actor</Th><Th>Target</Th><Th>Detail</Th><Th>When</Th></tr></thead>
          <tbody>{audit.map((a) => (
            <tr key={a.id}><Td>{a.action}</Td><Td>{a.actor_id ?? "—"}</Td><Td>{a.target_type || "—"}</Td><Td className="truncate max-w-[200px]">{a.detail || "—"}</Td><Td>{new Date(a.created_at).toLocaleDateString()}</Td></tr>
          ))}</tbody>
        </Table>
      )}
    </div>
  );
}

function KPI({ label, value }: any) {
  return <div className="card glass p-4"><p className="label">{label}</p><p className="text-2xl font-bold mt-1">{value}</p></div>;
}
function Table({ children }: any) {
  return <div className="card glass overflow-x-auto p-0"><table className="w-full text-sm">{children}</table></div>;
}
function Th({ children }: any) { return <th className="text-left p-3 font-medium text-ink-400 border-b border-ink-800">{children}</th>; }
function Td({ children }: any) { return <td className="p-3 border-b border-ink-800/60">{children}</td>; }
function ListCard({ title, items }: any) {
  return (
    <div className="card glass p-4">
      <h3 className="font-semibold mb-2">{title}</h3>
      <ul className="space-y-1 text-sm">
        {items.length === 0 ? <li className="text-ink-400">No data</li> :
          items.map((it: any, i: number) => <li key={i} className="flex justify-between"><span>{it.name || it.email}</span><span className="text-ink-400">{it.count}</span></li>)}
      </ul>
    </div>
  );
}
function BarChart({ data }: any) {
  const max = Math.max(1, ...data.map((d: any) => d.value));
  return (
    <div className="flex items-end gap-1 h-32">
      {data.map((d: any, i: number) => (
        <div key={i} className="flex-1 flex flex-col items-center justify-end gap-1" title={`${d.label}: ${inr(d.value)}`}>
          <div className="w-full bg-gradient-to-t from-brand-500/40 to-accent-500/70 rounded-t" style={{ height: `${(d.value / max) * 100}%` }} />
          <span className="text-[9px] text-ink-500">{d.label}</span>
        </div>
      ))}
    </div>
  );
}
function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
