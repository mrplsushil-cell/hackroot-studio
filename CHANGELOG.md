# CHANGELOG — Hackroot Studio

All notable changes to Hackroot Studio are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to SemVer.

## [1.0.0] — 2026-08-03 (Release Candidate 1)

### Added
- **AI video generation pipeline** — director + 9 specialized agents (Video Director,
  Prompt Analyzer, Script Writer, Scene Planner, Visual Generator, Voice Generator,
  Caption Generator, Renderer, Quality Control) producing a rendered MP4 via FFmpeg.
- **Credit system** — 10s=1 / 20s=2 / 30s=3 / 60s=5 credits; deduction on render;
  exhaustion blocks generation (402); full ledger in `/billing/credits/history`.
- **Subscription billing** — Free / Starter / Pro / Business plans; Razorpay checkout
  (mock + live modes); invoices; cancel/renew/change.
- **Library** — grid/list views, preview player, rename, duplicate, delete, download,
  search, filters, status badges, pagination.
- **Brand Kit** — logo upload, brand colors, fonts, website, voice, default toggle,
  live preview; auto-applied to renders.
- **Templates** — 8 built-in categories (Product Ad, Fashion Reel, Instagram Reel,
  YouTube Shorts, Corporate, Brand Story, Promotional Offer, Custom) + custom templates.
- **Public API** — API-key auth (SHA-256 hashed, scopes, monthly quota), generate-video /
  script / thumbnail endpoints.
- **Authentication** — JWT (HS256, 7-day), register/login, password reset (enum-safe),
  cross-user isolation.
- **Email events** — welcome, verify, password-reset, payment, subscription, invoice,
  video-ready via a provider abstraction (mock + SMTP).
- **Admin console** — user management, credit adjustment, subscriptions, invoices,
  logs, analytics, providers.
- **Deployment** — `docker-compose.prod.yml` (nginx reverse proxy), TLS-ready nginx
  config, `production.env.example`, backup/restore runbooks.
- **Security** — rate limiting (production-gated), upload magic-byte validation,
  audit/request logging, CSP.

### Changed
- Credit model clamped to a non-negative total (`grant_credits` floors at 0) — prevents
  negative balances from admin adjustments.
- Removed a duplicate `rate_limit_per_minute` declaration in `app/config.py` (effective
  value 60/min retained).

### Fixed
- Negative credit totals via admin credit adjustment (now clamped ≥ 0).
- Cross-user video access correctly returns 404 on all operations.

### Security
- JWT HS256 + `sub` validation; 401 on invalid/expired.
- Passwords hashed with bcrypt.
- Upload validation: extension + MIME + magic-byte sniff + size cap (rejects
  PHP-in-PNG, HTML-renamed-JPG, oversized).
- API keys stored hashed; full key shown once.
- 100% ORM/parameterized queries (no SQL injection surface).
- Secrets never exposed via API; `/settings` returns provider status only.

---

## [0.x] — Pre-release (development)
- Initial platform scaffolding, asset manager, brand-kit, templates, and the Phase-8
  SaaS monetization layer (billing, credits, public API, team, admin).
