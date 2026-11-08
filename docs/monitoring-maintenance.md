# Jellyfin Monitoring and Safe Maintenance

This document describes the operational monitoring and maintenance
procedures used for a Docker-based Jellyfin deployment.

The goal is to detect failures, validate dependencies and perform
controlled upgrades without unnecessarily disrupting the server.

## 1. Audited Environment

Audit date: November 7, 2026.

| Component | Audited result |
| --- | --- |
| Jellyfin | 12.4 |
| Container state | Running |
| Container health | Healthy |
| Restart policy | unless-stopped |
| Container restart count | 0 |
| Recent health checks | 5 successful |
| NVIDIA GPU | RTX 5060 Ti |
| NVIDIA driver | 580.178.04 |
| Jellyfin FFmpeg | 8.1.3-Jellyfin |
| Reverse proxy | Healthy |
| No-IP DUC | Active and enabled |
| Unhealthy Docker containers | 0 |

The GPU model and driver matched between the host and container.

## 2. Monitoring Architecture

```text
Jellyfin Application
        |
        v
Docker Health Check
        |
        +----> Healthy / Unhealthy
        |
        v
Operational Monitoring
        |
        +----> Container state
        +----> Restart count
        +----> Application logs
        +----> GPU availability
        +----> Storage capacity
        +----> Backup results
        +----> Reverse proxy / DDNS
```

Monitoring must cover both the application and its dependencies.

A healthy container does not prove that every playback feature,
library operation or external connection is working correctly.

## 3. Docker Health Check

The audited Jellyfin health check uses:

```text
Interval:       30 seconds
Timeout:        30 seconds
Retries:        3
Start period:   10 seconds
```

The five most recent recorded health check results returned exit
code zero.

Useful commands:

```bash
docker inspect jellyfin --format \
'{{.State.Health.Status}}'
```

```bash
docker inspect jellyfin --format \
'{{range .State.Health.Log}}{{println .ExitCode}}{{end}}'
```

A failed health check changes Docker's health state.

It does not automatically restart the container solely because
the state becomes unhealthy.

## 4. Restart Policy

The container uses:

```yaml
restart: unless-stopped
```

This helps restore the service after ordinary host or Docker
restarts unless the administrator intentionally stopped it.

At the time of the audit:

```text
RestartCount = 0
```

A restart policy is not a substitute for application monitoring.

## 5. Application Logs

Useful inspection command:

```bash
docker logs --since 24h jellyfin
```

Logs may contain filenames, paths or other private information.

Never publish complete production logs without sanitization.

### Log severity matters

During the November 7 audit, eight lines matched keywords such
as "error", "exception", "critical" or "fatal".

Classification:

```text
ERR:             1
INF:             6
Other/unknown:   1
Total matches:   8
```

A keyword match is not equivalent to a confirmed application error.

A follow-up investigation on November 8 classified three ERR
entries over a 72-hour period as Trickplay image-generation
failures involving System.ObjectDisposedException.

They occurred during Borg backup windows. A shutdown-related
interaction is plausible but remains unproven.

The maintenance audit now uses a dedicated severity-aware analyzer
rather than relying on error-related keywords.

## 6. GPU Monitoring

The host GPU should be accessible from inside Jellyfin.

Host:

```bash
nvidia-smi --query-gpu=name,driver_version \
  --format=csv,noheader
```

Container:

```bash
docker exec jellyfin nvidia-smi \
  --query-gpu=name,driver_version \
  --format=csv,noheader
```

The audited NVIDIA driver version matched on both sides.

After NVIDIA driver updates, GPU compatibility should be
validated again.

## 7. Transcoding Verification

The presence of NVENC encoders confirms available capabilities.

A real transcoding workload is necessary to verify operational
hardware acceleration.

Useful checks:

```bash
docker exec jellyfin sh -c '
/usr/lib/jellyfin-ffmpeg/ffmpeg -hide_banner -encoders |
grep -E "h264_nvenc|hevc_nvenc|av1_nvenc"
'
```

A forced playback transcode can then be inspected through
Jellyfin's FFmpeg logs.

Validation should distinguish:

- direct play;
- video transcoding;
- NVIDIA hardware encoding;
- GPU decoding and scaling;
- HDR to SDR tone mapping, when applicable.

These functions are not necessarily used during every playback.

## 8. Storage Monitoring

Application configuration and cache use the fast host filesystem.

Large media files are stored on Linux RAID1.

During the audit:

```text
Application filesystem: 70% used
Media RAID filesystem:  75% used
```

The mounts were:

```text
/config       read-write
/cache        read-write
/media        read-only
/media/Music  read-write
```

The specific Music write permission is intentional.

Storage utilization should be inspected before updates or
large library operations.

## 9. Backup Verification

Jellyfin application state is included in the host's Borg backup
workflow.

The latest audited full backup completed successfully:

```text
Date:    2026-11-07
Time:    03:59:17 WET
Result:  success
Exit:    0
```

Useful command:

```bash
systemctl show borg-backup-full.service \
  -p Result \
  -p ExecMainStatus \
  -p InactiveEnterTimestamp
```

A successful backup job does not independently prove that an
individual application file can be restored.

Archive contents and restore procedures must be verified separately.

## 10. Repository Verification

Borg repository checks run through a separate systemd timer.

The journal confirmed a successful repository check on:

```text
2026-11-01 09:39:39 WET
```

At the November 7 audit, the next execution was scheduled
for November 8.

Useful commands:

```bash
systemctl list-timers --all --no-pager |
grep borg-check-repository
```

```bash
journalctl -u borg-check-repository.service \
  --no-pager
```

Repository checking and testing application recovery serve
different purposes.

## 11. Reverse Proxy and DDNS

The external-access path depends on:

```text
Dynamic DNS
     |
     v
Nginx Proxy Manager
     |
     v
Jellyfin
```

During the audit:

```text
Reverse proxy: healthy
No-IP DUC:     active
Auto-start:    enabled
```

If external access fails but Jellyfin works locally, inspect
DNS and the reverse proxy before changing the Jellyfin container.

The project contains a separate documented DDNS outage.

## 12. Pre-Update Checklist

Before updating Jellyfin:

1. Identify the active Docker Compose project and service.
2. Confirm the currently running image and version.
3. Check recent application errors.
4. Confirm a recent successful backup.
5. Check recovery options for persistent configuration.
6. Verify available filesystem space.
7. Record current volumes, port bindings and GPU access.
8. Preserve a copy of the active Compose configuration.
9. Review the intended target version and release notes.
10. Check database compatibility and downgrade limitations.

The public repository does not contain production credentials
or the active server configuration.

## 13. Safe Update Procedure

Upgrades should be deliberate rather than automatic.

The general sequence is:

```text
Audit current state
        |
        v
Confirm backup / rollback
        |
        v
Select target release
        |
        v
Validate Docker Compose
        |
        v
Pull target image
        |
        v
Recreate only Jellyfin
        |
        v
Verify application
        |
        v
Verify GPU / playback
        |
        v
Accept or investigate
```

For a Compose-managed deployment, configuration should be
validated before applying changes:

```bash
docker compose config -q
```

After the administrator updates the intended image version,
the target service can be deployed using the verified
Compose project.

Avoid recreating unrelated containers.

Do not use `docker compose down` or Docker pruning commands
as routine steps for updating a single service.

## 14. Post-Update Validation

After an update:

- container reaches healthy state;
- application version matches the intended release;
- local HTTP endpoint responds;
- libraries and metadata are accessible;
- persistent mounts are unchanged;
- NVIDIA GPU is visible;
- FFmpeg encoders are available;
- a real playback/transcoding test succeeds;
- relevant logs contain no unexplained new failures;
- reverse proxy access still works;
- backup integration remains valid.

A healthy container alone is not enough to approve a major upgrade.

## 15. Rollback Planning

Before deployment, preserve:

```text
Previous image reference
Previous Compose configuration
Compatible application configuration backup
```

If the new release fails:

1. Preserve failure evidence and logs.
2. Identify the actual failing component.
3. Determine whether the update changed the application database.
4. Select a compatible image and configuration backup.
5. Validate the proposed rollback configuration.
6. Restore with Jellyfin stopped when database files are involved.
7. Start only the required service.
8. Verify libraries, access and hardware transcoding.

Downgrading the image alone may not be safe after database
schema changes.

Never assume older application versions can open newer databases.

## 16. Read-Only Audit Script

The repository provides:

```text
scripts/jellyfin-maintenance-audit.sh
```

This script reads:

- Docker container state;
- health-check results;
- restart counts;
- NVIDIA availability;
- Borg service results;
- reverse proxy and DDNS state;
- recent application log severity counts.

It does not update, stop, restart or recreate containers.

It also avoids printing raw production log messages.

## 17. Safety Principles

Operational maintenance follows this order:

```text
Observe
   |
   v
Diagnose
   |
   v
Plan / Backup
   |
   v
Change
   |
   v
Validate
   |
   v
Document
```

Do not change production services solely to produce Git commits.

A documented audit and a tested procedure are useful work
even when no configuration change is necessary.

## Conclusion

The audited Jellyfin environment was operational:

```text
Jellyfin healthy
No container restarts
GPU available
Backup successful
Reverse proxy healthy
DDNS updater active
```

The subsequent Trickplay investigation documented recurring
ERR entries during backup windows without claiming a proven
root cause.

Future maintenance should preserve the separation between
observation, diagnosis, changes and validation.
