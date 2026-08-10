"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: "📊" },
  { name: "Create Video", href: "/create", icon: "🎬" },
  { name: "My Videos", href: "/library", icon: "📁" },
  { name: "Templates", href: "/templates", icon: "📄" },
  { name: "Assets", href: "/assets", icon: "🖼️" },
  { name: "Brand Kit", href: "/brand-kit", icon: "🎨" },
  { name: "AI Agents", href: "/agents", icon: "🤖" },
  { name: "Settings", href: "/settings", icon: "⚙️" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token, setUser, clear } = useAuth();

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    api.auth.me().then(setUser).catch(() => {
      clear();
      router.push("/login");
    });
  }, [token, router, setUser, clear]);

  if (!user) return null; // or a loading spinner

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-ink-800/80 bg-ink-900/40 flex-shrink-0 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-ink-800/80">
          <span className="text-lg font-bold gradient-text">Hackroot Studio</span>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  isActive 
                    ? "bg-brand-500/10 text-brand-400" 
                    : "text-ink-300 hover:bg-ink-800/50 hover:text-ink-100"
                }`}
              >
                <span>{item.icon}</span>
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-ink-800/80">
          <div className="bg-ink-800/50 rounded-lg p-3 text-sm">
            <div className="flex justify-between items-center mb-2">
              <span className="text-ink-300">Credits</span>
              <span className="font-medium text-brand-400">
                {Math.max(0, user.credits_total - user.credits_used)}
              </span>
            </div>
            <div className="w-full h-1.5 bg-ink-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-brand-500 rounded-full" 
                style={{ width: `${Math.min(100, (user.credits_used / user.credits_total) * 100)}%` }}
              />
            </div>
          </div>
          
          <button 
            onClick={() => { clear(); router.push("/login"); }}
            className="mt-4 w-full text-left px-3 py-2 text-sm font-medium text-red-400 hover:bg-red-500/10 rounded-lg transition"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-grid">
        {/* Top Navbar */}
        <header className="h-16 border-b border-ink-800/80 glass flex items-center justify-between px-8 flex-shrink-0 sticky top-0 z-10">
          <div className="flex-1 max-w-lg">
            <input 
              type="text" 
              placeholder="Search videos, templates..." 
              className="w-full bg-ink-800/50 border border-ink-700/50 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-brand-500/50 transition"
            />
          </div>
          
          <div className="flex items-center gap-4 pl-4">
            <button className="text-ink-300 hover:text-ink-100">
              🔔
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-ink-800">
              <div className="w-8 h-8 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-sm">
                {(user.full_name || user.email).charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-ink-200 hidden sm:block">
                {user.full_name || user.email}
              </span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-8 relative">
          {children}
        </div>
      </main>
    </div>
  );
}
