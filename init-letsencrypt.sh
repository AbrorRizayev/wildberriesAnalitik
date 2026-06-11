#!/bin/sh
# One-time bootstrap of Let's Encrypt TLS certificates.
#
# nginx refuses to start when ssl_certificate points at a missing file, so we
# first drop a throwaway self-signed cert in place, start nginx, then replace it
# with a real cert obtained over the HTTP-01 (webroot) challenge.
#
# Run once on the server:   ./init-letsencrypt.sh
# Renewals afterwards are automatic (the certbot service runs `certbot renew`).
set -e

# ─────────── settings ───────────
DOMAINS="-d airastats.uz -d www.airastats.uz"
EMAIL="pulatovbek41@gmail.com"   # expiry / security notices from Let's Encrypt
STAGING=0                        # 1 = use LE staging (testing; avoids rate limits)
# ─────────────────────────────────

LIVE="./certbot/conf/live/airastats.uz"

mkdir -p ./certbot/conf ./certbot/www

# 1) Throwaway self-signed cert so nginx can boot with the 443 block.
if [ ! -e "$LIVE/fullchain.pem" ]; then
  echo "### Creating a temporary self-signed certificate ..."
  mkdir -p "$LIVE"
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "$LIVE/privkey.pem" \
    -out    "$LIVE/fullchain.pem" \
    -subj "/CN=airastats.uz"
fi

echo "### Starting nginx (and the rest of the stack) ..."
docker compose up -d

# 2) Remove the dummy cert so certbot writes the real one cleanly.
echo "### Removing the temporary certificate ..."
docker compose run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/airastats.uz \
         /etc/letsencrypt/archive/airastats.uz \
         /etc/letsencrypt/renewal/airastats.uz.conf" certbot

# 3) Request the real certificate via the webroot challenge.
echo "### Requesting the Let's Encrypt certificate ..."
STAGING_ARG=""
[ "$STAGING" != "0" ] && STAGING_ARG="--staging"
docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG $DOMAINS \
    --email $EMAIL --agree-tos --no-eff-email --force-renewal" certbot

# 4) Reload nginx with the real certificate.
echo "### Reloading nginx ..."
docker compose exec nginx nginx -s reload

echo "### Done — https://airastats.uz should now be live."