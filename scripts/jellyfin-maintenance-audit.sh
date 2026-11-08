#!/usr/bin/env bash

# Read-only Jellyfin operational audit.
# Does not stop, restart, recreate or modify services.

set -u

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not accessible."
    exit 1
fi

echo "=== JELLYFIN ==="

if ! docker inspect jellyfin --format \
'image={{.Config.Image}}
status={{.State.Status}}
health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}
restart={{.HostConfig.RestartPolicy.Name}}
restart_count={{.RestartCount}}'; then
    exit 1
fi

echo
echo "=== HEALTHCHECK CONFIGURATION ==="

docker inspect jellyfin --format \
'{{if .Config.Healthcheck}}interval={{.Config.Healthcheck.Interval}}
timeout={{.Config.Healthcheck.Timeout}}
retries={{.Config.Healthcheck.Retries}}
start_period={{.Config.Healthcheck.StartPeriod}}{{else}}not configured{{end}}'

echo
echo "=== RECENT HEALTHCHECK EXITS ==="

docker inspect jellyfin --format \
'{{if .State.Health}}{{range .State.Health.Log}}{{println .ExitCode}}{{end}}{{end}}'

echo
echo "=== HOST GPU ==="

nvidia-smi --query-gpu=name,driver_version \
    --format=csv,noheader 2>/dev/null || echo "Unavailable"

echo
echo "=== JELLYFIN GPU ==="

docker exec jellyfin nvidia-smi \
    --query-gpu=name,driver_version \
    --format=csv,noheader 2>/dev/null || echo "Unavailable"

echo
echo "=== CONTAINER MOUNTS ==="

docker inspect jellyfin --format \
'{{range .Mounts}}{{println .Destination .Mode}}{{end}}'

echo
echo "=== BORG BACKUP ==="

systemctl show borg-backup-full.service \
    -p Result -p ExecMainStatus -p InactiveEnterTimestamp

echo
echo "=== BORG REPOSITORY CHECK ==="

systemctl show borg-check-repository.service \
    -p Result -p ExecMainStatus -p InactiveEnterTimestamp

echo
echo "=== REVERSE PROXY ==="

docker inspect npm --format \
'status={{.State.Status}}
health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    2>/dev/null || echo "Unavailable"

echo
echo "=== NO-IP ==="

printf 'active='
systemctl is-active noip-duc 2>/dev/null || true

printf 'enabled='
systemctl is-enabled noip-duc 2>/dev/null || true

echo
echo "=== JELLYFIN ERR/FTL AUDIT (72H) ==="

python3 "$(dirname "${BASH_SOURCE[0]}")/jellyfin-log-audit.py" || exit 1

echo
echo "=== UNHEALTHY CONTAINERS ==="

docker ps --filter health=unhealthy \
    --format '{{.Names}} | {{.Status}}'

echo
echo "=== AUDIT COMPLETE ==="
