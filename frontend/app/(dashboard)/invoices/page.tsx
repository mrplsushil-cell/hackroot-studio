"use client";

import { useEffect, useState } from "react";
import { FileText, Download, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";

function inr(p: number) { return "₹" + (p / 100).toLocaleString("en-IN"); }
function date(d: string) { return new Date(d).toLocaleString("en-IN"); }

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setInvoices(await api.billing.invoices()); }
      catch { toast.error("Failed to load invoices"); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <Centered><Loader2 className="size-6 animate-spin" /></Centered>;

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <h1 className="text-3xl font-bold flex items-center gap-2"><FileText className="size-7" /> Invoices</h1>
      {invoices.length === 0 ? (
        <div className="card glass p-10 text-center text-ink-400">No invoices yet.</div>
      ) : (
        <div className="card glass divide-y divide-ink-800/70">
          {invoices.map((inv) => (
            <div key={inv.id} className="flex items-center gap-4 p-4">
              <div className="size-10 rounded-lg bg-ink-900 grid place-items-center"><FileText className="size-5 text-ink-300" /></div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">{inv.invoice_no}</p>
                <p className="text-xs text-ink-400">{date(inv.created_at)} · {inv.description || inv.billing_cycle}</p>
              </div>
              <span className={`chip ${inv.status === "paid" ? "chip-active" : ""}`}>{inv.status}</span>
              <span className="font-semibold w-24 text-right">{inr(inv.total_amount)}</span>
              <button
                onClick={() => toast("Invoice PDF download is wired to /billing/invoices/:id/download")}
                className="icon-btn" title="Download"
              ><Download className="size-4" /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Centered({ children }: any) {
  return <div className="grid place-items-center py-24 text-ink-400">{children}</div>;
}
