# VERSION — Hackroot Studio

```
Version: 1.0.0
Codename: Release Candidate 1 (RC1)
Release date: 2026-08-03
Status: Release Candidate (production-readiness complete)
Stack: FastAPI 0.111 · Next.js 14 (App Router) · PostgreSQL 16 · Redis 7 · Celery 5.4 · FFmpeg 7.1 · Docker
```

## Compatibility
- Python: 3.11+
- Node: 20+
- PostgreSQL: 12+
- Redis: 6+
- Docker / Docker Compose v2

## Release line
- 1.0.x — stable line. Patch releases for fixes; minor for backward-compatible features.
- API versioning: `/api/v1` (path-based). Breaking changes bump the `vN` segment.
