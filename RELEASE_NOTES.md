# Release Notes — Hackroot Studio v1.0.0 (RC1)

**Release date:** 2026-08-03
**Type:** Release Candidate 1
**Recommendation:** ✅ Launch-ready (no Critical/High open issues; see FINAL OUTPUT).

## Highlights
Hackroot Studio v1.0.0 is a complete, AI-powered vertical-video generation SaaS.
Users describe a video in plain language; the platform's 9-agent pipeline plans,
scripts, visualizes, voice-overs, captions, and renders a watermarked MP4 — then
serves it from the Library for preview and download. A credit-based economy,
Razorpay billing, brand kits, and a public API round out the product.

## Features (since 0.x)
- End-to-end AI video generation (prompt → MP4) with real FFmpeg rendering.
- 9-agent creative pipeline (director, prompt analyzer, script writer, scene planner,
  visual generator, voice generator, caption generator, renderer, QC).
- Credit engine with transparent formula and ledger.
- 4 subscription tiers (Free/Starter/Pro/Business) via Razorpay (mock + live).
- Library with grid/list, preview, rename, duplicate, delete, download, search, filters,
  status badges, pagination.
- Brand Kit (logo, colors, fonts, website, voice, default) auto-applied to renders.
- Templates (8 built-ins + custom).
- Public REST API with hashed API keys, scopes, and quotas.
- Auth (JWT), email notifications, admin console, deployment config.

## Architecture
- **Backend:** FastAPI (async), SQLAlchemy 2.0 (asyncpg), Celery + Redis worker,
  FFmpeg rendering, PostgreSQL.
- **Frontend:** Next.js 14 (App Router, TypeScript, Tailwind), code-split (max 126 KB
  First-Load JS).
- **Infra:** Docker Compose (dev + prod with nginx reverse proxy), TLS-ready,
  security headers, gzip, cache.

## Stack
FastAPI 0.111 · Pydantic 2.7 · SQLAlchemy 2.0 · Celery 5.4 · Redis 7 · PostgreSQL 16 ·
FFmpeg 7.1 · Next.js 14 · React 18 · Tailwind 3 · Docker.

## Known Limitations
- Mock AI providers are the default; configure real provider keys for non-synthetic
  output.
- Razorpay signature verification is skipped in mock mode (set both keys in prod).
- Local filesystem storage is the v1.0 default (S3+CDN deferred).
- No auto-created admin; promote a user via SQL (see ADMIN_GUIDE.md).
- Generation latency ~70s per 20s video on a single worker (scale workers for throughput).

## Future Roadmap
- S3 + CDN media storage.
- Real Razorpay webhook reconciliation + recurring subscriptions.
- Team member acceptance flow + per-resource RBAC.
- Email template management / i18n.
- Prometheus/Grafana metrics + alerting.
- Stripe alternative + invoice PDFs.

## Upgrade Notes
- Run `alembic upgrade head` against the production DB before first launch.
- Copy `production.env.example` → `production.env`; set strong secrets and `APP_ENV=production`.
- See `DEPLOYMENT.md`, `LAUNCH_CHECKLIST.md`, and `SECURITY_REPORT.md`.
