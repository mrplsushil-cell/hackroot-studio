"use client";

import { useEffect, useState } from "react";
import { CreditCard, ArrowDownToLine, History, Calendar, CheckCircle2, XCircle, Loader2, Crown } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";

function inr(paise: number) { return "₹" + (paise / 100).toLocaleString("en-IN"); }
function date(d: string) { return new Date(d).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" }); }

export default function BillingPage() {
  const [current, setCurrent] = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [credits, setCredits] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [c, inv, ch, p] = await Promise.all([
        api.billing.current(), api.billing.invoices(), api.billing.creditHistory(), api.billing.plans(),
      ]);
      setCurrent(c); setInvoices(inv); setCredits(ch); setPlans(p);
    } catch { toast.error("Failed to load billing"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const act = async (fn: () => Promise<any>, msg: string) => {
    setBusy(true);
    try { await fn(); toast.success(msg); await load(); }
    catch (e: any) { toast.error(e?.response?.data?.detail || "Action failed"); }
    finally { setBusy(false); }
  };

  const changePlan = async (slug: string, billing_cycle = "monthly") =>
    act(() => api.billing.change(slug, billing_cycle), `Switched to ${slug}`);

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  const sub = current?.subscription;
  const plan = current?.plan;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <h1 className="text-3xl font-bold flex items-center gap-2"><CreditCard className="size-7" /> Billing</h1>

      {/* Current plan */}
      <div className="card glass p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="size-11 rounded-xl bg-gradient-to-br from-brand-500/30 to-accent-500/20 grid place-items-center">
              <Crown className="size-5 text-white" />
            </div>
            <div>
              <p className="font-semibold text-lg">{plan?.name} {sub?.cancel_at_period_end && <span className="text-xs text-amber-300">(cancels at period end)</span>}</p>
              <p className="text-xs text-ink-400">
                {sub ? `${date(sub.current_period_start)} – ${date(sub.current_period_end)}` : "Free plan · no active subscription"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            {sub?.cancel_at_period_end ? (
              <button disabled={busy} onClick={() => act(api.billing.renew, "Subscription renewed")} className="btn-secondary">Renew</button>
            ) : sub ? (
              <button disabled={busy} onClick={() => act(api.billing.cancel, "Cancellation scheduled")} className="btn-ghost text-rose-300 hover:bg-rose-500/10">Cancel</button>
            ) : null}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Credits remaining" value={current.credits_remaining} />
          <Stat label="Credits used" value={current.credits_used} />
          <Stat label="Plan credits" value={plan?.credits_per_month >= 9999 ? "∞" : plan?.credits_per_month} />
          <Stat label="Watermark" value={plan?.has_watermark ? "On" : "Off"} />
        </div>
      </div>

      {/* Upgrade / downgrade */}
      <div className="card glass p-5 space-y-3">
        <h2 className="font-semibold">Change plan</h2>
        <div className="flex flex-wrap gap-2">
          {plans.filter((p) => p.slug !== plan?.slug).map((p) => (
            <button key={p.id} disabled={busy} onClick={() => changePlan(p.slug)}
              className="btn-secondary text-sm inline-flex items-center gap-1.5">
              {p.name} · {inr(p.price_monthly)}/mo
            </button>
          ))}
        </div>
      </div>

      {/* Invoices / payment history */}
      <div className="card glass p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><History className="size-4" /> Invoices & Payment History</h2>
        {invoices.length === 0 ? (
          <p className="text-sm text-ink-400">No invoices yet.</p>
        ) : (
          <div className="space-y-2">
            {invoices.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between p-3 rounded-lg bg-ink-900/50 border border-ink-800/70">
                <div>
                  <p className="font-medium text-sm">{inv.invoice_no}</p>
                  <p className="text-xs text-ink-400">{date(inv.created_at)} · {inv.description || inv.billing_cycle}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`chip ${inv.status === "paid" ? "chip-active" : ""}`}>{inv.status}</span>
                  <span className="font-medium">{inr(inv.total_amount)}</span>
                  <a href={api.videos.downloadUrl(inv.id).replace("/videos/", "/billing/invoices/") + "/download"} className="icon-btn" title="Download" onClick={(e) => { /* invoice download not wired */ e.preventDefault(); toast("Invoice download coming soon"); }}>
                    <ArrowDownToLine className="size-4" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Credit history */}
      <div className="card glass p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><Calendar className="size-4" /> Credit History</h2>
        <div className="space-y-1 max-h-64 overflow-y-auto scrollbar-thin">
          {credits.length === 0 ? (
            <p className="text-sm text-ink-400">No credit activity yet.</p>
          ) : credits.map((c) => (
            <div key={c.id} className="flex items-center justify-between py-2 border-b border-ink-800/50 text-sm">
              <div>
                <span className="capitalize font-medium">{c.reason.replace("_", " ")}</span>
                <span className="text-ink-400 text-xs ml-2">{date(c.created_at)}</span>
              </div>
              <span className={c.change < 0 ? "text-rose-300" : "text-emerald-300"}>
                {c.change > 0 ? "+" : ""}{c.change}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: any) {
  return (
    <div className="p-3 rounded-lg bg-ink-900/50 border border-ink-800/70">
      <p className="label">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
