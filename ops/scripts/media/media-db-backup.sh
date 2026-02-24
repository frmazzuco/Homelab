#!/bin/bash
set -euo pipefail

export PATH="$HOME/Tools/lima/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

resolve_colima_bin() {
  if [ -n "${COLIMA_BIN:-}" ] && [ -x "${COLIMA_BIN:-}" ]; then
    printf "%s\n" "$COLIMA_BIN"
    return
  fi
  if [ -x "$HOME/Tools/colima/colima" ]; then
    printf "%s\n" "$HOME/Tools/colima/colima"
    return
  fi
  if command -v colima >/dev/null 2>&1; then
    command -v colima
    return
  fi
}

COLIMA="$(resolve_colima_bin || true)"
if [ -z "${COLIMA:-}" ]; then
  echo "Colima nao encontrado."
  exit 1
fi

if ! "$COLIMA" status >/dev/null 2>&1; then
  echo "Colima nao esta rodando."
  exit 1
fi

engine() {
  "$COLIMA" ssh -- sudo nerdctl "$@"
}

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/arr/backups/databases}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
ARR_CONFIG_ROOT="${ARR_CONFIG_ROOT:-$HOME/arr/config}"
JELLYFIN_CONFIG_DIR="${JELLYFIN_CONFIG_DIR:-$HOME/jellyfin/config}"
ARR_CLOUDBEAVER_WORKSPACE="${ARR_CLOUDBEAVER_WORKSPACE:-$HOME/arr/cloudbeaver/workspace}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="stack-db-$TIMESTAMP"
RUN_DIR="$BACKUP_ROOT/$RUN_ID"
SQLITE_DIR="$RUN_DIR/sqlite"
MYSQL_DIR="$RUN_DIR/mysql"
META_DIR="$RUN_DIR/meta"
MANIFEST="$META_DIR/manifest.tsv"
TARGETS_FILE="$META_DIR/sqlite-targets.txt"
LOCK_DIR="$BACKUP_ROOT/.media-db-backup.lock"

mkdir -p "$SQLITE_DIR" "$MYSQL_DIR" "$META_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Backup ja em execucao (lock: $LOCK_DIR)."
  exit 1
fi

cleanup() {
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

touch "$MANIFEST"

echo "run_id=$RUN_ID"
echo "backup_root=$BACKUP_ROOT"
echo "started_at=$(date -Iseconds)"
echo

{
  echo "name,image,status"
  engine ps --format '{{.Names}},{{.Image}},{{.Status}}'
} > "$META_DIR/containers.csv"

discover_sqlite_targets() {
  : > "$TARGETS_FILE"

  local roots=(
    "$ARR_CONFIG_ROOT/jellyseerr"
    "$ARR_CONFIG_ROOT/sonarr"
    "$ARR_CONFIG_ROOT/radarr"
    "$ARR_CONFIG_ROOT/prowlarr"
    "$ARR_CONFIG_ROOT/bazarr"
    "$ARR_CONFIG_ROOT/sabnzbd"
    "$ARR_CONFIG_ROOT/uptime-kuma"
    "$ARR_CONFIG_ROOT/beszel_data"
    "$ARR_CONFIG_ROOT/lingarr"
    "$JELLYFIN_CONFIG_DIR/data"
    "$ARR_CLOUDBEAVER_WORKSPACE/.data"
  )

  local root
  for root in "${roots[@]}"; do
    if [ ! -d "$root" ]; then
      continue
    fi
    find "$root" -type f \
      \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) \
      ! -name '*-wal' \
      ! -name '*-shm' \
      ! -name '*.bak*' \
      ! -path '*/backup/*' \
      ! -path '*/backups/*' \
      ! -path '*/recovery-*/*' >> "$TARGETS_FILE"
  done

  sort -u "$TARGETS_FILE" -o "$TARGETS_FILE"
}

backup_sqlite_like_file() {
  local source_path="$1"
  local relative_path="${source_path#/}"
  local target_base="$SQLITE_DIR/$relative_path"
  local backup_file="$target_base.sqlite3"

  mkdir -p "$(dirname "$backup_file")"

  if /usr/bin/sqlite3 "$source_path" ".timeout 8000" ".backup \"$backup_file\"" >/dev/null 2>&1; then
    if [ "$(/usr/bin/sqlite3 "$backup_file" "PRAGMA quick_check;" 2>/dev/null | head -n 1)" = "ok" ]; then
      printf "SQLITE_BACKUP\t%s\t%s\n" "$source_path" "$backup_file" >> "$MANIFEST"
      return 0
    fi
  fi

  rm -f "$backup_file" "$backup_file-wal" "$backup_file-shm"

  local raw_file="$target_base.raw"
  cp -p "$source_path" "$raw_file"
  if [ -f "$source_path-wal" ]; then
    cp -p "$source_path-wal" "$raw_file-wal"
  fi
  if [ -f "$source_path-shm" ]; then
    cp -p "$source_path-shm" "$raw_file-shm"
  fi
  printf "RAW_COPY\t%s\t%s\n" "$source_path" "$raw_file" >> "$MANIFEST"
}

backup_mariadb_lingarr() {
  if ! engine ps --format '{{.Names}}' | grep -qx 'lingarr-db'; then
    printf "MARIADB_SKIP\tlingarr-db\tcontainer_not_running\n" >> "$MANIFEST"
    return 1
  fi

  local dump_file="$MYSQL_DIR/lingarr-db.sql.gz"
  if engine exec lingarr-db sh -lc 'command -v mariadb-dump >/dev/null 2>&1 || command -v mysqldump >/dev/null 2>&1'; then
    if engine exec lingarr-db sh -lc '
      DUMP_BIN="$(command -v mariadb-dump || command -v mysqldump)"
      exec "$DUMP_BIN" \
        --single-transaction \
        --quick \
        --routines \
        --triggers \
        --events \
        --hex-blob \
        --databases "$MARIADB_DATABASE" \
        -uroot \
        -p"$MARIADB_ROOT_PASSWORD"
    ' | gzip -9 > "$dump_file"; then
      printf "MARIADB_DUMP\tlingarr-db\t%s\n" "$dump_file" >> "$MANIFEST"
      return 0
    fi
  fi

  printf "MARIADB_FAIL\tlingarr-db\t%s\n" "$dump_file" >> "$MANIFEST"
  return 1
}

discover_sqlite_targets

sqlite_count=0
sqlite_errors=0
while IFS= read -r source_path; do
  [ -n "$source_path" ] || continue
  sqlite_count=$((sqlite_count + 1))
  if ! backup_sqlite_like_file "$source_path"; then
    sqlite_errors=$((sqlite_errors + 1))
    printf "SQLITE_FAIL\t%s\t-\n" "$source_path" >> "$MANIFEST"
  fi
done < "$TARGETS_FILE"

mariadb_errors=0
if ! backup_mariadb_lingarr; then
  mariadb_errors=$((mariadb_errors + 1))
fi

printf "RETENTION\t%s\t%s_days\n" "$BACKUP_ROOT" "$RETENTION_DAYS" >> "$MANIFEST"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'stack-db-*' -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

{
  echo "finished_at=$(date -Iseconds)"
  echo "run_dir=$RUN_DIR"
  echo "sqlite_targets=$sqlite_count"
  echo "sqlite_errors=$sqlite_errors"
  echo "mariadb_errors=$mariadb_errors"
  echo "manifest=$MANIFEST"
} > "$META_DIR/summary.txt"

cat "$META_DIR/summary.txt"

if [ "$sqlite_errors" -gt 0 ] || [ "$mariadb_errors" -gt 0 ]; then
  exit 1
fi
