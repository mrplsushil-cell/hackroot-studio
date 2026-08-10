"use client";

import { useEffect, useState } from "react";
import { Check, Sparkles, Zap, Crown, Building2, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";

const ICONS: Record<string, any> = {
  free: Sparkles, starter: Zap, pro: Crown, business: Building2,
};

function inr(paise: number) {
  return "₹" + (paise / 100).toLocaleString("en-IN");
}

export default function PricingPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [current, setCurrent] = useState<any>(null);
  const [yearly, setYearly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [p, c] = await Promise.all([api.billing.plans(), api.billing.current()]);
        setPlans(p); setCurrent(c);
      } catch { toast.error("Failed to load plans"); }
      finally { setLoading(false); }
    })();
  }, []);

  const subscribe = async (slug: string) => {
    setBusy(slug);
    try {
      const co = await api.billing.checkout(slug, yearly ? "yearly" : "monthly");
      // Mock mode: auto-verify to complete the subscription.
      await api.billing.verify({
        plan_slug: slug, billing_cycle: yearly ? "yearly" : "monthly",
        razorpay_order_id: co.order_id, razorpay_payment_id: co.order_id,
        razorpay_signature: "mock", razorpay_subscription_id: co.subscription_id,
      });
      toast.success(`Subscribed to ${slug}`);
      setCurrent(await api.billing.current());
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Subscription failed");
    } finally { setBusy(null); }
  };

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold">Pricing that scales with you</h1>
        <p className="text-ink-400">Start free. Upgrade when you're ready. Cancel anytime.</p>
        <div className="inline-flex items-center gap-3 mt-2">
          <span className={!yearly ? "text-white font-medium" : "text-ink-400"}>Monthly</span>
          <button onClick={() => setYearly((v) => !v)} className={`relative w-12 h-6 rounded-full transition ${yearly ? "bg-brand-500" : "bg-ink-700"}`}>
            <span className={`absolute top-0.5 size-5 rounded-full bg-white transition ${yearly ? "left-6" : "left-0.5"}`} />
          </button>
          <span className={yearly ? "text-white font-medium" : "text-ink-400"}>Yearly <span className="text-emerald-400 text-xs">save 2 months</span></span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {plans.map((p) => {
          const Icon = ICONS[p.slug] || Sparkles;
          const price = yearly ? p.price_yearly : p.price_monthly;
          const isCurrent = current?.plan?.slug === p.slug;
          return (
            <div key={p.id} className={`card glass p-5 flex flex-col ${isCurrent ? "ring-2 ring-brand-500/50" : ""}`}>
              <div className="flex items-center gap-2 mb-2">
                <div className="size-9 rounded-lg bg-gradient-to-br from-brand-500/30 to-accent-500/20 grid place-items-center">
                  <Icon className="size-4 text-white" />
                </div>
                <h3 className="font-semibold">{p.name}</h3>
              </div>
              <div className="mb-1">
                <span className="text-3xl font-bold">{inr(price)}</span>
                <span className="text-ink-400 text-sm">/{yearly ? "yr" : "mo"}</span>
              </div>
              <p className="text-xs text-ink-400 mb-4">{p.credits_per_month >= 9999 ? "Unlimited credits" : `${p.credits_per_month} credits / mo`}</p>
              <ul className="space-y-2 text-sm text-ink-300 flex-1">
                <Feat ok={!p.has_watermark}>No watermark</Feat>
                <Feat ok={p.video_limit === 0}>{p.video_limit === 0 ? "Unlimited videos" : `${p.video_limit} videos / mo`}</Feat>
                <Feat ok={p.priority_queue}>Priority rendering</Feat>
                <Feat ok={p.api_access}>API access</Feat>
                <Feat ok={p.team_members > 1}>Up to {p.team_members} team members</Feat>
              </ul>
              <button
                disabled={isCurrent || busy === p.slug}
                onClick={() => subscribe(p.slug)}
                className={`mt-5 w-full justify-center ${isCurrent ? "btn-secondary" : "btn-primary"} inline-flex items-center gap-2`}
              >
                {busy === p.slug ? <Loader2 className="size-4 animate-spin" /> : null}
                {isCurrent ? "Current Plan" : p.slug === "free" ? "Current" : "Subscribe"}
              </button>
            </div>
          );
        })}
      </div>

      <ComparisonTable plans={plans} />
    </div>
  );
}

function Feat({ ok, children }: any) {
  return (
    <li className="flex items-center gap-2">
      <Check className={`size-4 ${ok ? "text-emerald-400" : "text-ink-600"}`} />
      <span className={ok ? "" : "line-through opacity-60"}>{children}</span>
    </li>
  );
}

function ComparisonTable({ plans }: any) {
  const rows = [
    { label: "Credits / month", get: (p: any) => p.credits_per_month >= 9999 ? "Unlimited" : p.credits_per_month },
    { label: "Video limit", get: (p: any) => p.video_limit === 0 ? "Unlimited" : p.video_limit },
    { label: "Watermark", get: (p: any) => p.has_watermark ? "Yes" : "No", invert: true },
    { label: "Priority queue", get: (p: any) => p.priority_queue ? "✓" : "—", invert: true },
    { label: "API access", get: (p: any) => p.api_access ? "✓" : "—", invert: true },
    { label: "Team members", get: (p: any) => p.team_members },
    { label: "Price / mo", get: (p: any) => inr(p.price_monthly) },
  ];
  return (
    <div className="card glass overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-ink-300">
            <th className="text-left p-3 font-medium">Feature</th>
            {plans.map((p: any) => <th key={p.id} className="p-3 font-medium text-center">{p.name}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-t border-ink-800/70">
              <td className="p-3 text-ink-300">{r.label}</td>
              {plans.map((p: any) => (
                <td key={p.id} className="p-3 text-center">
                  {typeof r.get(p) === "boolean" ? (r.get(p) ? "✓" : "—") : r.get(p)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
