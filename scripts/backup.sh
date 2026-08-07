#!/bin/sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
backup_dir=${BACKUP_DIR:-./backups}
mkdir -p "$backup_dir"
pg_dump --format=custom --file="$backup_dir/career-crm-$(date +%Y%m%d-%H%M%S).dump" "$DATABASE_URL"
