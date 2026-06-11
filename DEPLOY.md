# AIRA — Production Deployment (Docker)

Stack: **Django + Gunicorn** (app) · **PostgreSQL 16** (database) · **nginx** (reverse proxy + static).
Everything runs via `docker compose`.

```
 internet ─▶ nginx :80 ─▶ gunicorn (web) :8000 ─▶ postgres (db) :5432
                 └── serves /static/ from a shared volume
```

## 1. Prerequisites
- Docker Engine 24+ and the Compose plugin (`docker compose version`).
- A server (VPS) and, for HTTPS, a domain pointed at it.

## 2. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and set at minimum:
- `SECRET_KEY` — generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- `DEBUG=False`
- `ALLOWED_HOSTS=airastats.uz,www.airastats.uz`
- `CSRF_TRUSTED_ORIGINS=https://airastats.uz,https://www.airastats.uz`
- `DB_PASSWORD` — a strong password
- `SECURE_SSL_REDIRECT=False` until TLS is terminated in front (then set `True`)

> The example `SECRET_KEY` from dev contains `$` characters which make Docker
> Compose print harmless "variable is not set" warnings. A key from
> `token_urlsafe` has none — use one in production.

## 3. Build & start
```bash
docker compose build
docker compose up -d
```
On startup the `web` container automatically:
1. waits for PostgreSQL,
2. compiles UZ/RU translations (`compilemessages`),
3. applies migrations (`migrate`),
4. collects static files (when `DEBUG=False`).

Check status / logs:
```bash
docker compose ps
docker compose logs -f web
```

## 4. Create the admin user
This is a multi-tenant app with **no public signup** — the admin creates customer
accounts in Django admin.
```bash
docker compose exec web python manage.py createsuperuser
```
Then log in at `/admin/` and create users/profiles.

## 5. HTTPS with Let's Encrypt (certbot)
TLS terminates at nginx using free Let's Encrypt certificates. The compose stack
includes a `certbot` service that obtains and auto-renews them; `nginx/default.conf`
already has the `:80` (ACME challenge + redirect) and `:443` (real site) blocks.

**Prerequisites:** the domain's DNS A/AAAA records must point at this server, and
ports **80 and 443** must be open. `openssl` must be available on the host (used
once to make a temporary self-signed cert so nginx can boot).

**First-time issuance** — run once on the server:
```bash
# email + domains are set at the top of the script; edit if needed.
./init-letsencrypt.sh
```
The script drops a throwaway self-signed cert in place, starts the stack, then
replaces it with a real certificate over the HTTP-01 challenge and reloads nginx.

> Testing the plumbing? Set `STAGING=1` at the top of `init-letsencrypt.sh` first
> to use Let's Encrypt's staging CA (browsers will warn, but you avoid the strict
> rate limits). Re-run with `STAGING=0` once it works.

**Then** set `SECURE_SSL_REDIRECT=True` in the **production** `.env` and apply:
```bash
docker compose up -d
```
nginx forwards `X-Forwarded-Proto: https`, which Django trusts via
`SECURE_PROXY_SSL_HEADER` — that is what makes the Secure CSRF/session cookies
work. (Keep `SECURE_SSL_REDIRECT=False` only for local `http://localhost` testing.)

**Renewal** is automatic: the `certbot` service runs `certbot renew` every 12h and
nginx reloads every 12h to pick up the new cert. Verify any time with:
```bash
docker compose run --rm certbot certbot certificates
```

## Common operations
```bash
# Update after a code change
docker compose build web && docker compose up -d web

# One-off management command
docker compose exec web python manage.py <command>

# Database backup / restore
docker compose exec db pg_dump -U "$DB_USER" "$DB_NAME" > backup.sql
cat backup.sql | docker compose exec -T db psql -U "$DB_USER" "$DB_NAME"

# Stop / remove (keeps DB volume)
docker compose down
```
Data lives in the `pgdata` Docker volume and survives `down`/`up`.
`docker compose down -v` **deletes the database** — use with care.

## Tuning (optional, via `.env`)
`GUNICORN_WORKERS` (default min((2·CPU)+1, 8)), `GUNICORN_TIMEOUT` (120s, raised
for large Excel parses), `HTTP_PORT` (host port nginx binds, default 80),
`LOG_LEVEL`.