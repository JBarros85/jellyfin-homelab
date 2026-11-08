#!/usr/bin/env python3
"""Read-only Jellyfin log audit without exposing raw log content."""

import argparse
import re
import subprocess
import sys
from collections import Counter, deque

parser = argparse.ArgumentParser()
parser.add_argument(
    "--stdin",
    action="store_true",
    help="Read synthetic or supplied log data from stdin",
)
args = parser.parse_args()

LEVEL_RE = re.compile(r"\[(ERR|FTL)\](?=\s|$)", re.I)
TIME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})"
)
EXCEPTION_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_.]*Exception)\b"
)

def classify(line):
    value = line.lower()

    if "trickplay" in value:
        return "Trickplay"
    if re.search(r"ffmpeg|transcod|encoder|decoder", value):
        return "Transcoding/FFmpeg"
    if re.search(r"database|sqlite|dbcontext", value):
        return "Database"
    if re.search(r"subtitle", value):
        return "Subtitles"
    if re.search(r"library|metadata|provider", value):
        return "Library/metadata"
    if re.search(r"socket|connection|httpclient|network", value):
        return "Network/HTTP"
    if "plugin" in value:
        return "Plugins"

    return "Unclassified"

def analyze(lines):
    counts = Counter()
    recent = deque(maxlen=20)
    pending = None
    remaining = 0
    total = 0

    for line in lines:
        level = LEVEL_RE.search(line)

        if level:
            timestamp = TIME_RE.search(line)

            if timestamp:
                day, hour = timestamp.groups()
            else:
                day, hour = "unknown-date", "unknown-time"

            entry = {
                "day": day,
                "time": hour,
                "level": level.group(1).upper(),
                "category": classify(line),
                "exception": "not identified",
            }

            recent.append(entry)
            counts[
                (entry["day"], entry["level"], entry["category"])
            ] += 1

            total += 1
            pending = entry
            remaining = 5
            continue

        if pending is not None and remaining > 0:
            exception = EXCEPTION_RE.search(line)

            if exception:
                pending["exception"] = (
                    exception.group(1).split(".")[-1]
                )
                pending = None

            remaining -= 1

    return total, counts, recent

if args.stdin:
    total, counts, recent = analyze(sys.stdin)
else:
    try:
        process = subprocess.Popen(
            [
                "docker",
                "logs",
                "--since",
                "72h",
                "--timestamps",
                "jellyfin",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
    except OSError:
        sys.exit("ERROR: unable to launch Docker log inspection")

    total, counts, recent = analyze(process.stdout)

    if process.wait() != 0:
        sys.exit("ERROR: Docker log inspection failed")

print("WINDOW=72h" if not args.stdin else "WINDOW=stdin")
print(f"TOTAL_ERR_FTL={total}")

print()
print("=== BY DATE / SEVERITY / CATEGORY ===")

if not counts:
    print("No ERR/FTL entries detected")

for (day, level, category), count in sorted(counts.items()):
    print(f"{day} | {level} | {category} | {count}")

print()
print("=== LAST ERRORS (UTC, MAX 20) ===")

for item in recent:
    print(
        f'{item["day"]} {item["time"]}Z'
        f' | {item["level"]}'
        f' | {item["category"]}'
        f' | {item["exception"]}'
    )

print()
print("Raw log messages are intentionally omitted.")
