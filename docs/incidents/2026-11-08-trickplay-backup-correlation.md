# Jellyfin Trickplay Errors During Backup Windows

**Investigation date:** November 8, 2026

**Components:** Jellyfin 12.4, Docker, Trickplay, Borg, systemd

**Status:** Correlation identified; root cause not conclusively proven.

## 1. Initial Observation

A routine Jellyfin maintenance audit identified messages
containing error-related keywords.

The initial keyword counter included informational messages,
so its total could not be interpreted as the number of
actual application errors.

A follow-up inspection focused specifically on log messages
marked ERR or FTL.

## 2. Confirmed Error

Three ERR entries were found between November 6 and 8.

All three originated from:

```text
Jellyfin.Server.Implementations.Trickplay.TrickplayManager
```

The reported failure was:

```text
Error creating trickplay images.
System.ObjectDisposedException:
Cannot access a disposed object.
```

The stack trace included:

```text
System.Threading.SemaphoreSlim.Release(Int32 releaseCount)
```

Trickplay generates thumbnail images used for video
timeline previews.

ObjectDisposedException indicates that code attempted to
access an object after it had been disposed.

The logs do not establish why that object had been disposed.

## 3. Timeline Correlation

All timestamps below are UTC.

| Date | Borg started | Trickplay ERR | Jellyfin started | Borg finished |
| --- | --- | --- | --- | --- |
| 2026-11-06 | 03:16:10 | 03:48:20 | 03:51:40 | 03:57:50 |
| 2026-11-07 | 03:19:13 | 03:48:41 | 03:58:03 | 03:59:17 |
| 2026-11-08 | 03:19:25 | 03:51:40 | 03:57:32 | 04:00:49 |

Every identified error occurred:

1. After the backup service started.
2. Before the next recorded Jellyfin startup.
3. Before the backup service finished.

The three errors also occurred at similar times of day.

## 4. Backup and Jellyfin Lifecycle

Inspection of the backup script confirmed calls to:

```bash
stop_if_exists jellyfin
start_if_exists jellyfin
```

This means the backup workflow includes controlled
Jellyfin stop and start operations.

The available audit did not establish the exact execution
timestamp of either individual function.

Therefore, the evidence supports a temporal relationship
but not a definitive causal conclusion.

## 5. Working Hypothesis

One plausible explanation is a lifecycle race:

```text
Trickplay image generation
            |
            v
Jellyfin begins shutting down
            |
            v
A shared synchronization object is disposed
            |
            v
Trickplay attempts another operation
            |
            v
ObjectDisposedException
```

This is a hypothesis, not a verified execution trace.

Other explanations have not been excluded.

## 6. Service Health

The November 8 audit confirmed:

```text
Jellyfin: healthy
Container automatic restart count: 0
Unhealthy Docker containers: 0
NVIDIA GPU: available
Nginx Proxy Manager: healthy
No-IP DUC: active
```

The restart counter does not exclude deliberate
stop/start operations performed by maintenance scripts.

All three daily Borg runs completed successfully.

The weekly Borg repository check on November 8 also
finished successfully.

No ongoing Jellyfin outage was observed.

## 7. Monitoring Improvement

The existing maintenance script previously counted
any log line containing:

```text
error
exception
critical
fatal
```

This could incorrectly count informational messages
that merely mention an error-related word.

The new analyzer instead matches explicit Jellyfin
severity markers:

```text
[ERR]
[FTL]
```

It also reports:

- UTC date and time;
- severity;
- error category;
- exception class, when found;
- totals by date and category.

The analyzer uses a 72-hour window.

It prints no raw log lines, media filenames, domains,
network addresses or credentials.

## 8. Validation Strategy

The analyzer supports synthetic test data through:

```bash
python3 scripts/jellyfin-log-audit.py --stdin
```

Ordinary production auditing uses:

```bash
python3 scripts/jellyfin-log-audit.py
```

No production configuration changes are required.

## 9. Decision

The investigation did not justify modifying the
working Jellyfin or Borg deployment.

No service restarts, backup schedule changes, Docker
reconfigurations or application upgrades were performed.

If errors continue, further investigation should correlate
the precise stop event, scheduled Trickplay activity and
Jellyfin shutdown logs.

Errors occurring outside backup windows would also
warrant separate analysis.

## 10. Lessons Learned

- Keyword counts are not reliable severity counts.
- Backup success and application log errors can coexist.
- Correlation does not prove causation.
- Scheduled maintenance can interact with background tasks.
- Monitoring should avoid exposing production log content.
- Read-only investigation should precede production changes.

## Conclusion

The investigation confirmed three recurring Trickplay errors
during Borg backup windows.

A shutdown-related interaction is plausible, but the exact
cause remains unverified.

The immediate improvement was more accurate, privacy-conscious
log monitoring rather than an unproven production fix.
