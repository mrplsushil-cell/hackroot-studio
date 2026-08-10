"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Wand2, Library, LayoutTemplate, Image as ImageIcon,
  Palette, Bot, Settings as SettingsIcon, Sparkles, CreditCard, Tag,
  Bell, ShieldCheck, Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/dashboard",  label: "Dashboard",   icon: LayoutDashboard },
  { href: "/create",     label: "Create Video", icon: Wand2 },
  { href: "/library",    label: "My Videos",    icon: Library },
  { href: "/templates",  label: "Templates",    icon: LayoutTemplate },
  { href: "/assets",     label: "Assets",       icon: ImageIcon },
  { href: "/brand-kit",  label: "Brand Kit",    icon: Palette },
  { href: "/agents",     label: "AI Agents",    icon: Bot },
  { href: "/pricing",    label: "Pricing",     icon: Tag },
  { href: "/billing",    label: "Billing",      icon: CreditCard },
  { href: "/invoices",   label: "Invoices",     icon: Tag },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/team",        label: "Team",         icon: Users },
  { href: "/settings",   label: "Settings",     icon: SettingsIcon },
  { href: "/admin",      label: "Admin",        icon: ShieldCheck },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-ink-800/80 bg-ink-950/80">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-ink-800/80">
        <div className="size-8 rounded-lg bg-gradient-to-br from-brand-500 to-accent-500 grid place-items-center">
          <Sparkles className="size-4 text-white" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="font-semibold tracking-tight">Hackroot</span>
          <span className="text-[10px] uppercase tracking-widest text-ink-400">Studio</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        {items.map((it) => {
          const active = pathname?.startsWith(it.href);
          const Icon = it.icon;
          return (
            <Link
              key={it.href}
              href={it.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
                active
                  ? "bg-gradient-to-r from-brand-500/20 to-accent-500/15 text-white border border-brand-500/30"
                  : "text-ink-300 hover:bg-ink-800/50 hover:text-white"
              )}
            >
              <Icon className="size-4" />
              {it.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-ink-800/80 px-4 py-4">
        <div className="rounded-lg border border-ink-800/80 bg-ink-900/60 p-3">
          <p className="text-xs text-ink-400">Hackroot Studio</p>
          <p className="text-sm font-medium text-ink-100">Create. Imagine. Generate.</p>
        </div>
      </div>
    </aside>
  );
}
