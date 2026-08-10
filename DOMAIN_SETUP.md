# DOMAIN_SETUP — Hackroot Studio v1.0

Point your domains at the server and prepare them for Let's Encrypt.

## 1. DNS records
Create A (and optionally AAAA) records at your registrar / DNS host:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `app` | `<server-ip>` | 300 |
| A | `api` | `<server-ip>` | 300 |
| AAAA | `app` | `<server-ipv6>` | 300 |
| AAAA | `api` | `<server-ipv6>` | 300 |

(Use a single domain, e.g. `hackroot.studio` for the app and
`api.hackroot.studio` for the API. The frontend expects `NEXT_PUBLIC_API_URL`
to point at the API origin.)

Verify propagation:
```bash
dig +short app.yourdomain.com
dig +short api.yourdomain.com
```

## 2. Configure the API base URL
In `production.env`:
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
FRONTEND_BASE_URL=https://app.yourdomain.com
CORS_ORIGINS=https://app.yourdomain.com,https://api.yourdomain.com
```

## 3. Open the firewall
Ports 80 and 443 must be reachable from the internet (the ACME challenge uses
port 80). See VPS_SETUP.md (ufw allows 80/tcp and 443/tcp).

## 4. Bring the stack up on HTTP first (optional sanity check)
You can start the stack before TLS is issued — nginx will serve HTTP and the
80→443 redirect simply has no HTTPS listener yet (certbot issuance needs port 80
to answer the challenge). Then issue the cert (SSL_SETUP.md) and reload nginx.

```bash
docker compose -f docker-compose.prod.yml --env-file production.env up -d --build
curl -I http://app.yourdomain.com/health
```

## 5. Notes
- Let's Encrypt rate limits: avoid repeated failed issuances; use
  `--staging` first if testing.
- Wildcard certs require DNS-01 challenge (not covered here; use the webroot
  method with explicit names).
- After TLS is live, the nginx config already 301-redirects HTTP→HTTPS and
  sends HSTS.
