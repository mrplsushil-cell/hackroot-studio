"use client";

import { useEffect, useState } from "react";
import { Users, UserPlus, Crown, Shield, Pencil, Eye, Trash2, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";

const ROLES = [
  { value: "owner", label: "Owner", icon: Crown },
  { value: "admin", label: "Admin", icon: Shield },
  { value: "editor", label: "Editor", icon: Pencil },
  { value: "viewer", label: "Viewer", icon: Eye },
];

export default function TeamPage() {
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setMembers(await api.team.members()); }
    catch (e: any) {
      if (e?.response?.status === 403) toast.error("Team workspace needs a Business plan");
      else toast.error("Failed to load team");
    }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const invite = async () => {
    if (!email.includes("@")) return toast.error("Enter a valid email");
    setBusy(true);
    try { await api.team.invite(email, role); toast.success("Invited"); setEmail(""); await load(); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Invite failed"); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    if (!confirm("Remove this member?")) return;
    try { await api.team.remove(id); setMembers((m) => m.filter((x) => x.id !== id)); }
    catch { toast.error("Remove failed"); }
  };

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <h1 className="text-3xl font-bold flex items-center gap-2"><Users className="size-7" /> Team Workspace</h1>

      <div className="card glass p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><UserPlus className="size-4" /> Invite member</h2>
        <div className="flex flex-wrap gap-2">
          <input className="input flex-1 min-w-[200px]" placeholder="teammate@company.com" value={email}
            onChange={(e) => setEmail(e.target.value)} />
          <select className="input w-40" value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <button disabled={busy} onClick={invite} className="btn-primary inline-flex items-center gap-1.5">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <UserPlus className="size-4" />} Invite
          </button>
        </div>
        <p className="text-xs text-ink-400">Roles: Owner (full), Admin (manage), Editor (create), Viewer (read).</p>
      </div>

      <div className="card glass divide-y divide-ink-800/70">
        {members.length === 0 ? (
          <p className="p-6 text-center text-ink-400">No team members yet.</p>
        ) : members.map((m) => {
          const Icon = ROLES.find((r) => r.value === m.role)?.icon || Eye;
          return (
            <div key={m.id} className="flex items-center gap-3 p-4">
              <div className="size-9 rounded-lg bg-ink-900 grid place-items-center"><Icon className="size-4 text-brand-300" /></div>
              <div className="flex-1">
                <p className="font-medium">{m.email}</p>
                <p className="text-xs text-ink-400 capitalize">{m.role} · {m.status}</p>
              </div>
              <button onClick={() => remove(m.id)} className="icon-btn hover:bg-rose-500/20 hover:text-rose-300" title="Remove"><Trash2 className="size-4" /></button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
