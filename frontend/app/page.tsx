"use client";
import Link from "next/link";
import {
  Sparkles, Wand2, Film, Bot, Palette, CreditCard, CheckCircle2,
  Star, ChevronDown, Zap, Globe, ShieldCheck, MessageSquare,
} from "lucide-react";

const FEATURES = [
  { icon: Wand2, title: "AI Script & Storyboard", desc: "Turn a prompt into a structured script and scene plan sized to your duration." },
  { icon: Bot, title: "9 Specialized Agents", desc: "Director, Script Writer, Scene Planner, Visual, Voice, Caption, Editor and QC agents." },
  { icon: Palette, title: "Brand Kit Aware", desc: "Your colors, fonts and logo are applied automatically to every render." },
  { icon: Film, title: "Real FFmpeg Rendering", desc: "Ken Burns motion, crossfades, burned captions and voiceover — genuine MP4 output." },
  { icon: CreditCard, title: "Credits & Plans", desc: "Pay only for what you generate. Free tier with watermark, Pro for priority rendering." },
  { icon: ShieldCheck, title: "Production Ready", desc: "Rate limiting, request logs, audit trail, API keys and admin analytics." },
];

const TESTIMONIALS = [
  { name: "Priya M.", role: "DTC Founder", text: "Shipped 40 product reels in a week. The brand kit alone saved us hours." },
  { name: "Arjun K.", role: "Agency Lead", text: "API access lets our team generate at scale. The credits model is fair." },
  { name: "Sara L.", role: "Creator", text: "From prompt to finished 9:16 video without touching an editor. Wild." },
];

const FAQ = [
  { q: "Do you really render the video?", a: "Yes. Hackroot uses FFmpeg to encode scenes, mix audio and burn captions — the output is a real MP4, not a placeholder." },
  { q: "What does a credit buy?", a: "10s ≈ 1 credit, 20s ≈ 2, 30s ≈ 3, 60s ≈ 5. Longer videos scale at 5 credits per 30s block." },
  { q: "Can I use my own logo and colors?", a: "Absolutely — the Brand Kit stores your logo, palette and fonts and applies them automatically." },
  { q: "Is there an API?", a: "Business plans include API keys for /generate-video, /script and /thumbnail with per-key quotas." },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-ink-800/80 bg-ink-950/80 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <span className="text-lg font-bold gradient-text">Hackroot Studio</span>
          <nav className="hidden md:flex items-center gap-6 text-sm text-ink-300">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#demo" className="hover:text-white">Demo</a>
            <a href="#pricing" className="hover:text-white">Pricing</a>
            <a href="#faq" className="hover:text-white">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/login" className="btn-ghost text-sm">Sign in</Link>
            <Link href="/pricing" className="btn-primary text-sm">Get started</Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="relative max-w-6xl mx-auto px-4 py-24 text-center space-y-6">
          <span className="chip chip-active mx-auto w-fit">AI Video Generation Platform</span>
          <h1 className="text-5xl md:text-6xl font-bold leading-tight">
            Create. Imagine. <span className="gradient-text">Generate.</span>
          </h1>
          <p className="text-lg text-ink-300 max-w-2xl mx-auto">
            Turn a single prompt into a finished, brand-ready vertical video — script,
            visuals, voiceover and captions, rendered with real FFmpeg.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link href="/pricing" className="btn-primary inline-flex items-center gap-2"><Sparkles className="size-4" /> Start free</Link>
            <a href="#demo" className="btn-secondary inline-flex items-center gap-2"><Film className="size-4" /> See a demo</a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-10">Everything you need to ship video</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="card glass p-5 space-y-3">
                <div className="size-10 rounded-lg bg-gradient-to-br from-brand-500/30 to-accent-500/20 grid place-items-center">
                  <Icon className="size-5 text-white" />
                </div>
                <h3 className="font-semibold">{f.title}</h3>
                <p className="text-sm text-ink-400">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Demo */}
      <section id="demo" className="max-w-4xl mx-auto px-4 py-16">
        <div className="card glass p-8 text-center space-y-4">
          <Film className="size-10 mx-auto text-brand-300" />
          <h2 className="text-2xl font-bold">From prompt to MP4</h2>
          <p className="text-ink-400 max-w-xl mx-auto">
            Describe what you want — e.g. “A 20-second promo for a kidswear brand” —
            and Hackroot plans, writes, generates visuals, narrates and renders it.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 text-sm">
            {["Prompt", "Script + Scenes", "Voiceover", "Rendered MP4"].map((s, i) => (
              <div key={s} className="p-3 rounded-lg bg-ink-900/60 border border-ink-800">{i + 1}. {s}</div>
            ))}
          </div>
          <Link href="/pricing" className="btn-primary inline-flex items-center gap-2 mt-2"><Zap className="size-4" /> Try it free</Link>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-10">Simple, scalable pricing</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {[
            { name: "Free", price: "₹0", feats: ["2 videos/mo", "Watermark", "2 credits"] },
            { name: "Starter", price: "₹299", feats: ["25 videos/mo", "No watermark", "25 credits"] },
            { name: "Pro", price: "₹999", feats: ["150 videos/mo", "Priority queue", "150 credits"] },
            { name: "Business", price: "₹2999", feats: ["Unlimited", "Team + API", "Priority support"] },
          ].map((p) => (
            <div key={p.name} className="card glass p-5 flex flex-col">
              <h3 className="font-semibold">{p.name}</h3>
              <p className="text-2xl font-bold my-2">{p.price}<span className="text-sm text-ink-400">/mo</span></p>
              <ul className="space-y-1.5 text-sm text-ink-300 flex-1">
                {p.feats.map((f) => <li key={f} className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" />{f}</li>)}
              </ul>
              <Link href="/pricing" className="btn-secondary mt-4 justify-center">Choose {p.name}</Link>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="max-w-5xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-10">Loved by creators & teams</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className="card glass p-5 space-y-3">
              <div className="flex gap-0.5 text-amber-400"><Star className="size-4" /><Star className="size-4" /><Star className="size-4" /><Star className="size-4" /><Star className="size-4" /></div>
              <p className="text-sm text-ink-200">“{t.text}”</p>
              <p className="text-xs text-ink-400">{t.name} · {t.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="max-w-3xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-10">FAQ</h2>
        <div className="space-y-3">
          {FAQ.map((f) => (
            <details key={f.q} className="card glass p-4 group">
              <summary className="flex items-center justify-between cursor-pointer font-medium">
                {f.q}<ChevronDown className="size-4 group-open:rotate-180 transition" />
              </summary>
              <p className="text-sm text-ink-400 mt-2">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* Contact / CTA */}
      <section id="contact" className="max-w-4xl mx-auto px-4 py-16">
        <div className="card glass p-8 text-center space-y-3">
          <MessageSquare className="size-8 mx-auto text-brand-300" />
          <h2 className="text-2xl font-bold">Ready to generate?</h2>
          <p className="text-ink-400">Sign up free — no credit card required.</p>
          <Link href="/pricing" className="btn-primary inline-flex items-center gap-2"><Sparkles className="size-4" /> Get started</Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-ink-800/80">
        <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-ink-400">
          <span className="font-bold gradient-text text-base">Hackroot Studio</span>
          <div className="flex items-center gap-4">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#pricing" className="hover:text-white">Pricing</a>
            <a href="#faq" className="hover:text-white">FAQ</a>
            <span className="inline-flex items-center gap-1"><Globe className="size-4" /> hackroot.studio</span>
          </div>
          <span>© {new Date().getFullYear()} Hackroot Studio</span>
        </div>
      </footer>
    </div>
  );
}
