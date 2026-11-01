# Jellyfin Homelab

A real-world Jellyfin deployment running in a Linux homelab with Docker,
NVIDIA GPU acceleration, RAID-backed media storage, reverse proxy access,
backup automation and operational troubleshooting.

This repository documents the architecture and engineering decisions behind the
deployment while keeping production addresses, domains, credentials and
internal infrastructure details private.

## Project Goals

The project focuses on:

- running Jellyfin as a Docker service;
- separating application state from large media storage;
- using NVMe storage for configuration, database and cache;
- storing media on redundant RAID storage;
- enabling NVIDIA hardware acceleration;
- providing HTTPS access through a reverse proxy;
- integrating the service into backup and monitoring routines;
- documenting real operational incidents and troubleshooting.

## Architecture

```text
                     Internet
                        |
                        v
                Reverse Proxy / TLS
                        |
                        v
                 Jellyfin Container
                  TCP 8096 internal
                        |
          +-------------+-------------+
          |                           |
          v                           v
 Application state                 Media
 Config / DB / Cache               Library
          |                           |
          v                           v
        NVMe                        RAID1

                        +
                        |
                        v
                 NVIDIA GPU
              NVENC / NVDEC / CUDA
```

See:

- [Architecture](docs/architecture.md)
- [Docker Compose example](docker/docker-compose.example.yml)

## Storage Model

The deployment intentionally separates two different workloads.

### Application state

Configuration, database files, metadata, plugins and cache are stored on fast
local storage.

```text
Fast storage
├── config
└── cache
```

### Media

Large media files remain on redundant bulk storage.

```text
RAID1
└── media
    ├── Movies
    ├── Series
    └── Music
```

This avoids placing database/cache I/O on the media disks while keeping large
files on storage designed for capacity and redundancy.

## GPU Acceleration

The Jellyfin container receives access to an NVIDIA GPU through the NVIDIA
Container Toolkit.

The production environment uses hardware acceleration for tasks such as:

- hardware decoding;
- hardware encoding;
- CUDA processing;
- HDR to SDR tone mapping;
- H.264 encoding;
- HEVC encoding;
- AV1 encoding.

Hardware transcoding will be documented separately with a real validated
transcoding workflow.

## External Access

External access is not provided by publishing Jellyfin directly to the
internet.

The general path is:

```text
Client
  |
  v
HTTPS Reverse Proxy
  |
  v
Jellyfin
```

TLS, Dynamic DNS and reverse proxy behavior will be documented in later stages
of this project.

## Backup

Application configuration is included in the wider homelab backup strategy.

The media library and application state have different backup requirements, so
the project treats them separately.

Backup integration and consistency procedures will be documented in a dedicated
section.

## Repository Structure

```text
jellyfin-homelab/
├── README.md
├── .gitignore
├── docs/
│   └── architecture.md
└── docker/
    └── docker-compose.example.yml
```

## Planned Documentation

Future stages will cover:

- NVIDIA GPU and hardware transcoding;
- FFmpeg and NVENC/NVDEC validation;
- HDR to SDR tone mapping;
- storage migration and layout;
- backup consistency;
- reverse proxy and HTTPS access;
- Dynamic DNS;
- health monitoring;
- safe upgrade procedures;
- recovery and rollback;
- real troubleshooting incidents.

## Privacy

This is a public portfolio repository.

Production-specific information is intentionally excluded, including:

- real LAN and VPN addresses;
- public IP addresses;
- real domain names;
- DDNS credentials;
- API keys;
- private filesystem paths;
- certificate private keys;
- authentication credentials.

Examples use sanitized values instead.
