# SSL_SETUP — Hackroot Studio v1.0 (Let's Encrypt, automatic)

The production stack ships a `certbot` container that issues and **auto-renews**
Let's Encrypt certificates via the ACME webroot challenge. nginx is already
configured to proxy `/.well-known/acme-challenge/` and to terminate TLS from
`/etc/nginx/certs/fullchain.pem` + `privkey.pem`.

## 1. Prerequisites
- DNS records point at this server (DOMAIN_SETUP.md).
- Ports 80 + 443 open (ufw).
- Stack running: `docker compose -f docker-compose.prod.yml --env-file production.env up -d --build`.

## 2. Issue the certificate (first time)
Replace the email/domains with yours. The webroot is shared into the certbot
container at `/var/www/certbot` and into nginx at the same path.

```bash
COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
$COMPOSE run --rm certbot certonly --webroot -w /var/www/certbot \
  --email admin@yourdomain.com --agree-tos --no-eff-email \
  -d app.yourdomain.com -d api.yourdomain.com
```

Certbot writes to the `certs` volume at `/etc/letsencrypt/live/<domain>/`. We
need `fullchain.pem` + `privkey.pem` available to nginx at
`/etc/nginx/certs/`. Two options:

**Option A (recommended):** make the `certs` volume a bind mount to a host dir
and copy the live certs there, OR point nginx at the letsencrypt live path.
Simplest: change the nginx `certs` volume mount in `docker-compose.prod.yml` to:
```yaml
      - certs:/etc/letsencrypt:ro
```
and set in `nginx/nginx.conf`:
```nginx
ssl_certificate     /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/app.yourdomain.com/privkey.pem;
```
Both `certs` and `certbot`'s `certs` volume are the same Docker volume, so the
certbot-written files are visible to nginx. (This is the default in the shipped
compose file — `certs:/etc/nginx/certs:ro` — adjust the nginx `ssl_certificate`
paths to the live dir, or symlink.)

**Option B:** copy after issuance:
```bash
sudo mkdir -p /opt/hackroot/certs
sudo cp "$($COMPOSE ps -q certbot >/dev/null; docker volume inspect hackrootai_certs -f '{{.Mountpoint}}')/live/app.yourdomain.com/fullchain.pem" /opt/hackroot/certs/
sudo cp "$(docker volume inspect hackrootai_certs -f '{{.Mountpoint}}')/live/app.yourdomain.com/privkey.pem" /opt/hackroot/certs/
# then mount - ./certs:/etc/nginx/certs:ro and keep ssl_certificate /etc/nginx/certs/fullchain.pem
```

## 3. Reload nginx to pick up the cert
```bash
$COMPOSE exec nginx nginx -s reload
curl -I https://app.yourdomain.com/health    # expect 200 + Strict-Transport-Security header
```

## 4. Automatic renewal
The `certbot` service runs `certbot renew` every 12h and exits; the container's
loop restarts it. After renewal, nginx must reload to use the new cert. Add a
deploy hook (renewal runs this after success):
```bash
# on the host, create /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh
#!/bin/sh
docker compose -f /opt/hackroot/docker-compose.prod.yml --env-file /opt/hackroot/production.env exec nginx nginx -s reload
```
chmod +x it. (certbot auto-discovers `renewal-hooks/deploy`.)

## 5. Staging / testing
To avoid rate limits while testing, add `--staging` to the `certonly` command;
it uses the Let's Encrypt staging CA (not trusted by browsers) but validates
the flow.

## 6. Verify
```bash
echo | openssl s_client -connect app.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
curl -I https://app.yourdomain.com/   # 200, HSTS header present
```
