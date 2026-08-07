# Production deployment

Run `docker compose -f docker-compose.prod.yml up -d` to place Gunicorn behind the supplied TLS-enabled Nginx configuration. Set `SERVER_NAME`, `TLS_CERT_DIR`, `POSTGRES_PASSWORD`, and a random `SECRET_KEY` in the environment. Never commit `.env`.

Apply `flask db upgrade` once per release before switching traffic. Probe `/health` for readiness. Container logs go to stdout/stderr for collection by the host.

## Backup and restore

Schedule `scripts/backup.sh` daily with `DATABASE_URL` and an off-host `BACKUP_DIR`. Encrypt backups, restrict access, define retention, and periodically test recovery in an isolated database. Restore with `scripts/restore.sh BACKUP_FILE`; it replaces objects in the selected database, so verify the target first.

## HTTPS

Use an automatically renewed certificate (for example, Let's Encrypt) or Cloudflare Tunnel. Forward `X-Forwarded-Proto`; the app trusts one proxy hop in production.
