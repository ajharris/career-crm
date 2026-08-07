#!/bin/sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${1:?Usage: scripts/restore.sh BACKUP_FILE}"
pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$1"
