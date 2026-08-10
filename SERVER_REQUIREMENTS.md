# SERVER_REQUIREMENTS — Hackroot Studio v1.0

Minimum and recommended specs for a production deployment of the full stack
(nginx + frontend + backend + worker + postgres + redis).

## Minimum (low traffic / pilot)
- **CPU:** 2 vCPU
- **RAM:** 4 GB
- **Disk:** 40 GB SSD (plus room for `/data/storage` media growth)
- **OS:** Ubuntu 24.04 LTS (or any Linux with Docker Engine 24+ / Compose v2)
- **Network:** 1 Gbps, ports 80 + 443 open

## Recommended (production)
- **CPU:** 4 vCPU (FFmpeg rendering is CPU-bound; scale `worker` horizontally for throughput)
- **RAM:** 8 GB
- **Disk:** 100 GB SSD (size `/data/storage` for generated MP4s + thumbnails + brand-kit logos)
- **Bandwidth:** unmetered or ≥2 TB/month if serving many video downloads
- **OS:** Ubuntu 24.04 LTS, fully patched
- **Network:** ports 80 + 443 open; IPv4 + IPv6

## Required software (on the host)
| Component | Version | Notes |
|---|---|---|
| Docker Engine | 24.0+ | `docker-ce` |
| Docker Compose | v2.20+ | plugin (`docker compose`), not `docker-compose` v1 |
| `curl`, `git`, `gzip`, `tar` | any | backup scripts depend on them |
| (optional) `certbot` | latest | only if not using the bundled `certbot` container |
| (optional) `ufw` | default | host firewall |

## Storage considerations
- `postgres_data` volume: small (a few GB even at scale).
- `storage_data` volume: **grows with usage** — each 20s 9:16 video is ~1 MB MP4
  plus a thumbnail. Budget ~2–5 MB per generated video; size the disk accordingly
  or move to S3 + CDN (see deployment guide).
- `redis_data`: transient (in-flight tasks); not backed up.

## Resource assignments (compose defaults)
- `backend`: 4 Uvicorn workers.
- `worker`: Celery `--concurrency=4`.
- `redis`: capped at 512 MB, `allkeys-lru`.
- `postgres`: not exposed to the host (internal network only).

## Domain
- One A/AAAA record for the web app (e.g. `app.domain.com`) and one for the API
  (e.g. `api.domain.com`), or a single domain serving both on paths.
- Let's Encrypt requires port 80 reachable for the ACME http-01 challenge.
