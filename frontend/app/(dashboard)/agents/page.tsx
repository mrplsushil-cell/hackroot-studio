"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bot, Clapperboard, Search, FileText, LayoutGrid, Image as ImageIcon,
  Mic, Captions, Film, ShieldCheck, Loader2, Cpu,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, Agent } from "@/lib/api";

const ICONS: Record<string, any> = {
  director: Clapperboard, script: FileText, scenes: LayoutGrid, visual: ImageIcon,
  voice: Mic, editor: Film, qc: ShieldCheck, analyzer: Search, captions: Captions,
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setAgents(await api.agents.list()); }
    catch (e) { toast.error("Failed to load agents"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2"><Bot className="size-7" /> AI Agents</h1>
        <p className="text-ink-400 mt-1">The autonomous agents that turn your prompt into a finished video.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {agents.map((a) => {
          const Icon = ICONS[a.id] || Cpu;
          const ready = a.status === "ready";
          return (
            <div key={a.id} className="card glass p-5 space-y-3">
              <div className="flex items-center gap-3">
                <div className="size-11 rounded-xl bg-gradient-to-br from-brand-500/30 to-accent-500/20 grid place-items-center">
                  <Icon className="size-5 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold leading-tight">{a.name}</h3>
                  <p className="text-xs text-ink-400">{a.role}</p>
                </div>
                <span className={`chip ${ready ? "chip-active" : ""}`}>
                  <span className={`size-2 rounded-full ${ready ? "bg-emerald-400" : "bg-amber-400"}`} />
                  {a.status}
                </span>
              </div>
              <p className="text-sm text-ink-300">{a.description}</p>
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
