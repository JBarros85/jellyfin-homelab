# Jellyfin Storage and Backup Strategy

This document describes the storage architecture and Borg backup
integration of a real Jellyfin deployment running in a Linux homelab.

The design separates high-performance application storage, redundant
media storage, and independent backup storage.

## 1. Architecture

The deployment uses three storage layers:

```text
                  Jellyfin Docker
                        |
             +----------+----------+
             |                     |
             v                     v
          NVMe SSD             RAID1 HDD
             |                     |
       +-----+-----+               |
       |           |               |
     /config     /cache          /media
       |                           |
       |                     Movies / Series
       |                           |
       |                         Music
       |
       v
  Borg Backup Workflow
       |
       v
  Separate Backup HDD
```

### Storage roles

| Storage | Purpose |
| --- | --- |
| NVMe SSD | Configuration, database, metadata, plugins, cache |
| RAID1 HDD | Large media files |
| Separate HDD | Borg backup repository |

The three storage layers have different operational purposes.

RAID1 provides disk redundancy but is not a replacement for backups.

---

## 2. Application Storage on NVMe

Jellyfin application state is stored on the NVMe filesystem.

The main persistent directory is mounted into the container as:

```text
/config
```

It contains data such as:

- application settings;
- databases;
- metadata;
- plugin configuration;
- persistent application state.

The cache directory is mounted as:

```text
/cache
```

Cache and temporary transcoding data benefit from faster storage
but are generally rebuildable.

### Why NVMe?

Jellyfin frequently accesses databases and small metadata files.

Keeping those operations on the NVMe reduces the amount of random I/O
performed by the mechanical media disks.

---

## 3. RAID1 Media Storage

Large media files remain on Linux software RAID1.

The audited array reported:

```text
RAID level:       RAID1
State:            clean
Active devices:   2
Working devices:  2
Failed devices:   0
Array status:     [UU]
```

Both RAID members were operational during the audit.

The media directory is mounted into the Jellyfin container as:

```text
/media
```

A sanitized Compose example:

```yaml
volumes:
  - /srv/media:/media:ro
```

The main media tree is mounted read-only to limit unnecessary
modifications by the application.

---

## 4. Writable Music Directory

The production deployment intentionally allows writes to the
music directory.

A sanitized representation:

```yaml
volumes:
  - /srv/media:/media:ro
  - /srv/media/Music:/media/Music:rw
```

This creates two access levels:

```text
/media         -> read-only
/media/Music   -> read-write
```

The specific Music mount is intentional and should not be removed
simply because it overlaps with the general media mount.

---

## 5. Storage Utilization

During the audit on November 3, 2026:

| Storage | Total | Used | Available | Usage |
| --- | --- | --- | --- | --- |
| NVMe filesystem | 936G | 606G | 291G | 68% |
| RAID1 media filesystem | 3.6T | 2.6T | 892G | 75% |
| Backup filesystem | 2.7T | 1.3T | 1.4T | 49% |

These values are an operational snapshot, not fixed capacity limits.

The separation allows each storage layer to be monitored independently.

---

## 6. Borg Backup Integration

The homelab uses BorgBackup for scheduled backups.

The Jellyfin deployment is integrated into the existing host-level
backup workflow.

The audited backup script contains references to:

```text
Persistent Jellyfin configuration
Container stop operation
Container restart/cleanup operation
```

The relevant operations include:

```bash
stop_if_exists jellyfin
```

and:

```bash
start_if_exists jellyfin
```

The script also includes the persistent Jellyfin configuration directory
among its backup sources.

The goal is to protect application state while reducing the risk of
capturing an actively changing database.

The complete execution order should always be verified in the active
backup script before making changes to this workflow.

---

## 7. Backup Consistency

A consistent application backup should avoid copying databases while
they are actively being modified.

The intended workflow is:

```text
Prepare backup
      |
      v
Pause Jellyfin safely
      |
      v
Capture persistent application state
      |
      v
Restore Jellyfin operation
      |
      v
Complete backup workflow
```

The active Borg script includes Jellyfin stop and restart operations.

Any backup workflow involving stopped services must provide a reliable
cleanup path in case an operation fails.

A successful systemd service result confirms completion of that backup
job, but it does not independently prove that every expected file was
included in its archive.

---

## 8. Automated Backup Schedule

The full backup is managed through systemd:

```text
borg-backup-full.timer
borg-backup-full.service
```

The backup runs on a daily schedule.

During the November 3 audit, the latest execution reported:

```text
Result:          success
ExecMainStatus:  0
Completion:      2026-11-03 04:16:58 WET
```

The service was not restarted or manually executed for this audit.

---

## 9. Borg Repository Verification

A separate scheduled operation checks the Borg repository:

```text
borg-check-repository.timer
borg-check-repository.service
```

The check runs weekly.

The most recent audited execution reported:

```text
Result:          success
ExecMainStatus:  0
Completion:      2026-11-01 09:39:39 WET
```

Repository verification and application restoration are different
procedures.

A healthy repository check does not replace a tested restore.

---

## 10. Recovery Strategy

Persistent configuration is the critical component required to restore
Jellyfin application settings and metadata.

A recovery workflow should:

1. Confirm a suitable Borg archive exists.
2. Verify that the archive contains the expected configuration files.
3. Stop Jellyfin before restoring application databases.
4. Preserve the current configuration for rollback.
5. Restore the selected configuration into the correct directory.
6. Verify ownership and filesystem permissions.
7. Start Jellyfin.
8. Validate application health, libraries and GPU access.

Restoration commands should be tailored to the actual archive and
deployment state.

No production restoration was performed during this audit.

---

## 11. Backup Coverage Limitations

The current audit confirmed:

- the persistent configuration path is referenced in the backup script;
- the script includes Jellyfin stop/restart operations;
- the latest daily backup service completed successfully;
- the latest repository check completed successfully.

The following items were not independently tested during this audit:

- exact file membership of the newest Borg archive;
- full restoration of Jellyfin configuration;
- complete media library backup coverage;
- recovery time after a simulated failure.

These remain separate verification tasks.

---

## 12. Monitoring Commands

### Container health

```bash
docker inspect jellyfin --format \
'{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
```

### Container mounts

```bash
docker inspect jellyfin --format \
'{{range .Mounts}}{{println .Mode .Destination}}{{end}}'
```

### RAID status

```bash
cat /proc/mdstat
sudo mdadm --detail /dev/md0
```

### Filesystem utilization

```bash
df -hT
```

### Last Borg backup

```bash
systemctl show borg-backup-full.service \
  -p Result \
  -p ExecMainStatus \
  -p InactiveEnterTimestamp
```

### Last repository check

```bash
systemctl show borg-check-repository.service \
  -p Result \
  -p ExecMainStatus \
  -p InactiveEnterTimestamp
```

---

## 13. Operational Safety

Before modifying storage or backup configuration:

- verify the current mounts;
- confirm the latest successful backup;
- inspect affected scripts;
- preserve rollback options;
- avoid unnecessary service restarts;
- do not run destructive RAID operations;
- do not publish Borg credentials or repository encryption material.

The backup repository must remain protected independently from
the application and media filesystems.

---

## Conclusion

The Jellyfin storage design combines:

```text
NVMe application state
          +
RAID1 media storage
          +
Separate Borg backup disk
          +
Automated backup jobs
          +
Repository verification
          =
Layered storage protection
```

The verified result is a healthy storage environment with a successful
scheduled backup and repository check.

Archive-level recovery verification remains a future operational task.
