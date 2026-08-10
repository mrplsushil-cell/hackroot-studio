# =============================================================================
# Hackroot Studio — nginx (brotli-enabled, built locally)
# =============================================================================
# Built from Alpine's nginx + nginx-mod-http-brotli (same package repo, so the
# dynamic module is guaranteed ABI-compatible). Gives Brotli compression without
# depending on an external brotli image. The main config is mounted from
# ./nginx/nginx.conf at runtime and loads the module via `load_module`.
FROM alpine:3.20

RUN apk add --no-cache nginx nginx-mod-http-brotli brotli

# Alpine's nginx requires the worker to run as root by default; keep defaults.
# The brotli module .so lives in /usr/lib/nginx/modules and is loaded by the
# top-level `load_module` directives in the mounted nginx.conf.
RUN mkdir -p /var/log/nginx /var/lib/nginx /run/nginx \
    && touch /var/log/nginx/access.log /var/log/nginx/error.log

EXPOSE 80 443
STOPSIGNAL SIGTERM

# Run nginx in foreground.
CMD ["nginx", "-g", "daemon off;"]
