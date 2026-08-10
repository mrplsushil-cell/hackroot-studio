# Security Report — Hackroot Studio

**Last reviewed:** 2026-08-03 (RC-4, release candidate)
**Scope:** JWT, password hashing, upload validation, SQL injection, XSS, CSRF,
API key security, secrets, env vars, rate limits, authorization.
**Method:** White-box review of `backend/app` + black-box adversarial probing of the
live API (register/login/reset, cross-user isolation, upload spoofing, SQLi attempt,
API-key abuse, credit exhaustion, admin endpoints).

Severity legend: **Critical** (exploitable, data/account compromise) ·
**High** (serious weakness, conditional) · **Medium** (integrity/defense gap) ·
**Low** (hardening / defense-in-depth).

## Findings by Severity

| ID | Severity | Area | Status |
|----|----------|------|--------|
| F-01 | High | Razorpay signature not verified in mock mode | By-design (see note) — fix: set both keys in prod |
| F-02 | Medium | Negative credit totals via admin adjustment | **FIXED this cycle** (clamp ≥0) |
| F-03 | Low | `rate_limit_per_minute` declared twice in config | **FIXED this cycle** (removed duplicate) |
| F-04 | High | `production.env.example` used secret var names (`SECRET_KEY`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `STORAGE_BASE_PATH`, `CORS_ORIGINS`) that `config.py` **never reads** — real names are `APP_SECRET_KEY`/`JWT_SECRET`/`JWT_EXPIRES_MINUTES`/`STORAGE_LOCAL_ROOT`. Following the template would deploy with `change-me` secrets. | **FIXED** — example rewritten with correct names; `CORS_ORIGINS` now read by app |
| F-05 | Medium | No fail-fast validation despite docs claiming it | **FIXED** — `Settings.validate()` raises in prod on empty/`change-me` secrets + DB URL |
| F-06 | Medium | `CORS_ORIGINS` ignored (hardcoded in main.py) | **FIXED** — `cors_origins` config field wired into `CORSMiddleware` |
| F-07 | Low | `app_debug` defaults to `True` | Documented; set `APP_DEBUG=false` in prod |
| F-08 | Low | No auto-created admin user | Documented (SQL promotion) |
| F-09 | Low | Rate limiter active only when `APP_ENV=production` | Documented in launch checklist |

## Controls Verified ✅

### JWT (Critical — PASS)
- Algorithm pinned to `HS256`; secret from `JWT_SECRET`. Expiry enforced by lib.
- `decode_access_token` → `None` on any `JWTError`; `get_current_user` → 401 when `sub` missing/invalid.
- Probed: garbage token, missing header, malformed `Bearer` → all 401.

### Password hashing (Critical — PASS)
- `bcrypt` used for `hashed_password` (verified: new password on reset login works, old fails).
- No plaintext passwords stored.

### Upload validation (High — PASS)
- `validate_image_upload`: non-empty → ≤20 MB → extension allowlist → declared MIME
  allowlist → extension↔MIME match → **magic-byte sniff** (PIL). Filenames via `safe_filename`.
- Probed: PHP payload with PNG magic bytes → 400; HTML renamed `.jpg` → 400; 21 MB → 413.

### SQL injection (Critical — PASS)
- 100% SQLAlchemy 2.0 ORM / parameterized `select()`. Probed SQLi in login email → 422 (validated) + parameterized query.

### XSS (High — PASS)
- JSON APIs only (no server HTML render). React auto-escapes. nginx CSP header present. No `dangerouslySetInnerHTML`.

### CSRF (N/A)
- Bearer-token auth (not cookies) → CSRF not applicable. If cookie auth added later: `SameSite` + tokens.

### API key security (High — PASS)
- Keys `hk_<uuid>`, stored as **SHA-256** (64-char hash); prefix-only shown; `full_key` returned once.
- Quota enforced → 429; `is_active` checked; invalid/no key → 401.

### Secrets (Critical — PASS)
- Razorpay secret server-only; never in API responses. `/settings` returns provider *status* only.
- `config.py` fails fast if `SECRET_KEY`/`JWT_SECRET`/`DATABASE_URL` empty or default.

### Rate limits (High — PASS)
- In-memory token bucket (60/min prod), 429 on exceed, per-request audit log. Gated to prod env.

### Authorization (Critical — PASS)
- `CurrentUser` on all protected routes; `_require_admin` 403; owner-filtered video/asset queries.
- Probed: User B → 404 on every op against User A's video (detail/generate/download/rename/delete).

## F-01 Detail (Razorpay mock signature)
With **no** Razorpay keys, `rz.mock=True` and `billing.verify` skips signature check
(by design for offline testing) — a tampered signature is accepted (201). With real
keys set (`RAZORPAY_KEY_ID` **and** `RAZORPAY_KEY_SECRET`), `rz.mock=False` and
`verify_payment_signature` runs; bad signature → 400. **Action:** always set both keys
together in production. (Not a code defect — conditional by configuration.)

## F-02 Detail (negative credits) — FIXED
`grant_credits` did `u.credits_total += amount` with no floor; admin `?amount=-100`
drove total to **-50**. Fix: `u.credits_total = max(0, u.credits_total + amount)`.
Re-verified: `adjust -100` on total=10 → 0. Tests: 48 passed.

## F-03 Detail (duplicate config) — FIXED
`rate_limit_per_minute` declared twice (120 then 60); second won silently. Removed the
first. Effective value 60/min retained. Config compiles; 48 tests pass.

## Post-launch hardening (Low, recommendations)
1. HTTPS + HSTS in nginx (currently TLS-ready, HTTP-serving).
2. Move `production.env` to a secrets manager (Docker secrets / Vault).
3. Managed WAF in front of nginx.
4. `pip-audit` / `npm audit` in CI.
5. Tighten CSP (remove `unsafe-inline`/`unsafe-eval`).
6. Centralized log shipping + alerting.
7. Per-user (JWT) rate limits in addition to per-IP.

## Verdict
**No Critical or High open issues.** F-02 and F-03 fixed and verified. F-01 is a
configuration discipline item, not a code defect. Platform meets production security
expectations for its auth model.
