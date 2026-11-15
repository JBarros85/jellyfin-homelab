# Jellyfin Backup and Disaster Recovery Runbook

**Audit date:** November 15, 2026

**Environment:** Ubuntu Linux, Docker Compose, Jellyfin 12.4,
BorgBackup 1.4.4 and Linux RAID1.

**Status:** Backup infrastructure validated.
Application restore testing remains pending.

## 1. Objective

This runbook documents the backup architecture and recovery
procedures for a self-hosted Jellyfin installation.

The goal is to protect application state, minimize downtime
and recover safely without disrupting unrelated Docker services.

## 2. Storage Architecture

```text
Ubuntu Server
    |
    +-- Docker Compose
    |       |
    |       +-- Jellyfin
    |             +-- /config       RW
    |             +-- /cache        RW
    |             +-- /media        RO
    |             +-- /media/Music  RW
    |
    +-- NVMe: Application configuration and cache
    |
    +-- RAID1: Media library
    |
    +-- Separate disk: Borg backup repository
```

Production paths, domains and IP addresses are omitted.

RAID1 provides redundancy against certain disk failures,
but is not a substitute for backups.

## 3. Audit Results

On November 15, 2026:

| Component | Result |
| --- | --- |
| Jellyfin image | jellyfin/jellyfin:12.4 |
| Container status | Running |
| Container health | Healthy |
| Restart count | 0 |
| NVMe filesystem usage | 69% |
| Media RAID usage | 75% |
| Borg version | 1.4.4 |
| Borg repository directory | Present |
| Latest daily backup | Success |
| Latest weekly repository check | Success |

The restart count applies to the current container instance.

## 4. Backup Schedule and Results

Daily backups run through a systemd timer.

Recent completed executions:

| Date | Start (WET) | Finish (WET) |
| --- | --- | --- |
| 2026-11-12 | 03:17:10 | 04:15:41 |
| 2026-11-13 | 03:17:53 | 04:09:01 |
| 2026-11-14 | 03:16:18 | 03:58:04 |
| 2026-11-15 | 03:17:30 | 04:12:02 |

The latest execution returned:

```text
Result=success
ExecMainStatus=0
```

The weekly repository-check service also completed
successfully on November 15 at 09:23:20 WET.

Its next scheduled execution was November 22, 2026.

## 5. Jellyfin Backup Integration

The existing backup script references the persistent
Jellyfin configuration directory.

It also includes:

```bash
stop_if_exists jellyfin
start_if_exists jellyfin
```

These operations are intended to coordinate Jellyfin
with the backup procedure.

Their presence in the script does not independently prove
that every individual archive contains the required files.

## 6. Backup Validation Levels

| Check | Status |
| --- | --- |
| Backup repository exists | Confirmed |
| Scheduled backup service succeeds | Confirmed |
| Weekly repository check succeeds | Confirmed |
| Jellyfin files verified inside an archive | Pending |
| Isolated extraction test | Pending |
| Full application recovery test | Pending |

A successful backup execution must not be confused
with a successful restoration.

## 7. Recovery Scenario: Container Failure

If Jellyfin stops working while its data remains intact:

1. Inspect Docker container state and application logs.
2. Verify the existing Compose configuration.
3. Confirm persistent volumes and their permissions.
4. Check the latest backup result.
5. Identify the failure before restarting anything.
6. Recreate only the affected service if justified.
7. Validate application health and playback.

A controlled service recreation can be performed from
the verified Compose project:

```bash
docker compose config -q

docker compose up -d \
  --no-deps \
  --no-build \
  --pull never \
  --force-recreate \
  jellyfin
```

WARNING: This interrupts Jellyfin temporarily.

It must not be executed before checking the image,
volumes, configuration and available backup.

## 8. Recovery Scenario: Corrupted Configuration

If application configuration or databases are damaged:

1. Preserve the current state for investigation.
2. Select a suitable backup recovery point.
3. Verify the relevant files inside the Borg archive.
4. Prepare a separate restoration directory.
5. Confirm available storage space.
6. Extract the selected data into the isolated location.
7. Validate ownership, permissions and file contents.
8. Confirm compatibility with the Jellyfin version.
9. Stop Jellyfin before replacing live database files.
10. Validate the restored application.

Never extract directly over live application state
without a recovery plan.

Downgrading only the application image may be unsafe
if database schema changes have occurred.

## 9. Recovery Scenario: Media Storage Failure

If the media RAID becomes unavailable:

1. Assess RAID and physical disk condition.
2. Avoid unnecessary writes.
3. Determine whether redundancy remains available.
4. Verify which media directories have independent backups.
5. Prepare appropriate replacement storage.
6. Restore verified media data when required.
7. Recheck library access and playback.

The current audit did not establish complete media
backup coverage.

## 10. Recovery Scenario: Host Failure

A full recovery may require:

```text
Ubuntu installation
        |
        v
Storage configuration
        |
        v
Docker and Compose
        |
        v
NVIDIA driver and container integration
        |
        v
Persistent Jellyfin configuration
        |
        v
Media library
        |
        v
Reverse proxy and Dynamic DNS
        |
        v
Application and playback validation
```

Recovery also requires access to the relevant
backup encryption keys and credentials.

These must never be committed to a public repository.

## 11. Isolated Restore Test Plan

A future non-destructive restoration test should:

1. Identify an appropriate Borg archive.
2. Confirm Jellyfin configuration files are present.
3. Allocate a separate temporary restoration location.
4. Extract a limited set of files.
5. Verify file readability and metadata.
6. Validate expected database files.
7. Record the outcome.
8. Remove only confirmed temporary test data.

No extraction or full restoration was performed
during the November 15 audit.

## 12. Post-Recovery Acceptance Criteria

A successful application recovery should confirm:

- Jellyfin starts and becomes healthy.
- Configuration and user accounts are preserved.
- Media libraries are available.
- Playback works correctly.
- NVIDIA GPU access is operational.
- Hardware transcoding works when required.
- HTTPS access through the reverse proxy works.
- Dynamic DNS resolves correctly.
- Backup automation remains operational.

A healthy Docker container alone is not sufficient.

## 13. Recovery Objectives

The backup workflow is scheduled daily.

However, a guaranteed Recovery Point Objective (RPO)
has not yet been established.

A Recovery Time Objective (RTO) also remains unknown
because a complete recovery has not been timed.

Both require validation using actual recoverable data.

## 14. Operational Checks

Container health:

```bash
docker inspect jellyfin --format \
'{{.State.Health.Status}}'
```

Backup service:

```bash
systemctl show borg-backup-full.service \
  -p Result -p ExecMainStatus -p InactiveEnterTimestamp
```

Repository check:

```bash
systemctl show borg-check-repository.service \
  -p Result -p ExecMainStatus -p InactiveEnterTimestamp
```

Scheduled jobs:

```bash
systemctl list-timers --all --no-pager |
grep -E 'borg-backup-full|borg-check-repository'
```

These commands are read-only.

## 15. Lessons Learned

- Successful backup jobs do not prove restoration.
- RAID1 does not replace independent backups.
- Persistent application configuration is critical.
- Recovery must preserve Docker mount permissions.
- Database compatibility matters during rollback.
- Restoration testing should be isolated from production.
- Recovery procedures should be documented before failure.

## Conclusion

The November 15 audit confirmed successful daily backup
automation and a successful weekly repository check.

Jellyfin was healthy and its persistent mounts were identified.

Archive content verification and application restore testing
remain pending.

This runbook provides a controlled plan for completing
those validations without unnecessary production changes.
