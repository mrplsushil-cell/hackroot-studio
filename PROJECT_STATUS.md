# PROJECT STATUS — Hackroot Studio

**Version target:** v1.0.0 (Release Candidate 1)
**Date:** 2026-08-03
**Prepared by:** RC-1 repository audit (independent, full-stack)
**Status:** ✅ Feature-complete and production-candidate. One data-integrity bug fixed this cycle
(negative credit totals, re-verified). No Critical/High open issues.

---

## 1. Completed Features

| Subsystem | Status | Notes |
|---|---|---|
| **Frontend** (Next.js 14, App Router, 19 pages, ~3.4k LOC) | ✅ | Auth, dashboard, create, library, brand-kit, templates, billing, pricing, invoices, settings, team, agents, assets, notifications, admin. `tsc --noEmit` clean, `npm run build` clean, code-split (max 126 KB First-Load JS). |
| **Backend** (FastAPI, ~6.9k LOC) | ✅ | 48 pytest passing. All routers mounted. |
| **Auth** | ✅ | JWT (HS256, 7-day), register/login, password reset (enum-safe), cross-user isolation verified. |
| **Authorization** | ✅ | `CurrentUser` on all protected routes; `_require_admin` 403 for superuser; owner-filtered video/asset queries. |
| **Billing / Subscriptions** | ✅ | 4 plans (free/starter/pro/business), checkout (Razorpay mock), verify, cancel, renew, change, invoices, credit ledger. |
| **Credits** | ✅ | Formula 10s=1/20s=2/30s=3/60s=5; deduction on render; exhaustion returns 402; admin adjust clamped ≥0 (fixed this cycle). |
| **Video generation** | ✅ | Async Celery job, director pipeline (9 agents), render to MP4. |
| **MP4 rendering / FFmpeg** | ✅ | ffmpeg 7.1.5 in backend + worker; real h264 720x1280 + aac output (verified via ffprobe). |
| **Watermark** | ✅ | Burned on free plan ("Made with Hackroot Studio"), disabled on paid (verified). |
| **Brand Kit** | ✅ | Logo upload (50 MB cap), colors, fonts, website, voice, default toggle, live preview. |
| **Templates** | ✅ | 8 built-in categories + custom templates. |
| **Library** | ✅ | Grid/list, preview, rename, duplicate, delete, download, search, filters, status badges, pagination. |
| **AI Agents** | ✅ | 9 agents exposed via `/agents`. |
| **Settings** | ✅ | Provider status surfaced (no secrets), profile. |
| **Public API** | ✅ | API-key auth (SHA-256 hashed), scopes, monthly quota (429), scripts/thumbnails/video. |
| **Email events** | ✅ | Welcome, verify, password-reset, payment, subscription, invoice, video-ready via provider abstraction (mock verified). |
| **Rate limiting** | ✅ | In-memory token bucket, gated to `APP_ENV=production`. |
| **Database** | ✅ | PostgreSQL + async SQLAlchemy; 3 Alembic migrations; FKs indexed. |
| **Redis / Celery** | ✅ | Redis broker (db 1), worker concurrency 4, queue draining to 0. |
| **Docker** | ✅ | `docker-compose.yml` (dev) + `docker-compose.prod.yml` (nginx + prod), valid config. |
| **Deployment config** | ✅ | nginx TLS-ready, security headers, gzip, cache, rate-limit; `production.env.example`; backup/restore runbooks. |

## 2. Optional Features (not in v1.0, deferred)

- S3 storage backend + CDN (local filesystem is the v1.0 default).
- Real Razorpay webhook reconciliation + recurring subscriptions (mock verify used pre-launch).
- Team member acceptance flow + per-resource RBAC enforcement (invite exists; acceptance is stub).
- Email template management / i18n.
- Prometheus/Grafana metrics + alerting (manual monitoring documented).
- Stripe alternative / invoice PDF generation.

## 3. Technical Debt

- **`scripts/` directory is empty** — no backup/restore automation script shipped; procedure is documented manually in BACKUP.md/RECOVERY.md. Recommended: add `scripts/backup.sh` + `scripts/restore.sh`.
- **`max_upload_size_mb` config (50 MB) only applies to Brand-Kit logos**; image uploads use a hardcoded 20 MB cap in `app/utils/uploads.py` (deliberate but not configurable).
- **Rate limiter disabled outside `APP_ENV=production`** — fine for tests, but depends on the env var being set correctly in prod (documented in LAUNCH_CHECKLIST).
- **No auto-created admin user** — promotion requires a one-off SQL `UPDATE users SET is_superuser=true`. Documented in ADMIN_GUIDE.md.
- **Credit model ambiguity** — new `User` rows are seeded with `credits_total=100` (model default / signup balance), while the **Free plan** grants only `credits_per_month=2` (video_limit 2, watermark on). These are distinct: 100 is the starting balance, 2 is the monthly Free-plan allowance. Confirm the intended starting balance before launch (currently a new user can generate ~50×20s videos on the seed balance alone).
- **`app_debug` defaults to `True`** — must be overridden to `False` in production (fail-fast does not yet enforce this; documented).
- **Mock providers are the default** — real provider keys must be configured before launch for non-synthetic output.

## 4. Known Issues

- **Mock-mode Razorpay signature not verified** (by design): with no Razorpay keys, a tampered signature is accepted. With real keys (`RAZORPAY_KEY_ID` **and** `RAZORPAY_KEY_SECRET`), `rz.mock` is `False` and verification runs. If only `KEY_ID` is set without secret, `mock` stays `True` and verification is skipped — ensure both are set together. (Security note, not a code defect.)
- **Generation latency** ~70s for a 20s 9:16 video on a single worker (mock providers). Dominant cost is FFmpeg; scale workers horizontally for throughput.
- **Bandwidth/host note (local only):** on this dev host, port 8000 is shadowed by an unrelated local PHP process, so `curl localhost:8000` from the host fails; in-container requests and nginx routing are unaffected. Not a product issue.

## 5. Security Notes

See `SECURITY_REPORT.md` for the full matrix. Summary:
- JWT HS256 + `sub` validation; 401 on invalid/expired. ✅
- Passwords hashed with bcrypt. ✅
- Upload validation: extension + MIME + magic-byte sniff (PIL) + size cap; rejected PHP-in-PNG, HTML-renamed-JPG, 21 MB. ✅
- SQL: 100% ORM / parameterized. ✅
- XSS: JSON APIs, React auto-escape, nginx CSP. ✅
- CSRF: N/A (Bearer-token auth, not cookies). ✅
- API keys: SHA-256 hashed, full key shown once, quota enforced. ✅
- Secrets: never returned by API; `/settings` exposes status only. ✅
- Rate limiting: production-gated. ✅
- **Fixed this cycle:** negative credit totals via admin adjustment (clamp ≥0).

## 6. Performance Notes

- Frontend bundle: max 126 KB First-Load JS (library), 87 KB shared — well code-split, no action needed.
- DB: FK columns indexed; eager loading (`selectinload`) on videos/scenes and subscription→plan prevents N+1.
- Redis: 1.7 MB used, queue empty in idle state.
- Worker: concurrency 4; horizontal `--scale worker=N` recommended for load.
- FFmpeg: dominant render cost (~70s/video at mock quality); tune CRF/preset or scale workers for production throughput.
- No memory leaks observed during the audit (idle worker/backend stable).
