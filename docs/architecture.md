# Jellyfin Architecture

## Overview

The Jellyfin deployment is designed around separation of responsibilities.

The application runs in Docker while different storage classes are used for
application state and media.

```text
                         External Client
                               |
                               v
                         HTTPS / TLS
                               |
                               v
                        Reverse Proxy
                               |
                               v
                     +------------------+
                     |     Jellyfin     |
                     |      Docker      |
                     +------------------+
                       |       |       |
              +--------+       |       +--------+
              |                |                |
              v                v                v
          NVMe State        RAID Media      NVIDIA GPU
       config / cache      movies/music    NVENC/NVDEC
```

---

## Container Layer

Jellyfin runs as a Docker container using a pinned application image.

The production deployment uses:

```text
jellyfin/jellyfin:12.4
```

A fixed version is preferred over blindly following a moving image tag because
upgrades can then be performed deliberately and validated before being accepted
as the new operational state.

The container uses:

```text
restart: unless-stopped
```

This allows the service to return automatically after normal host or Docker
restarts unless it was deliberately stopped by the administrator.

---

## Storage Separation

The deployment separates application state from the media library.

### Fast storage

Application data benefits from lower latency and higher random-I/O performance.

This includes:

```text
configuration
database
metadata
plugins
logs
cache
temporary transcode data
```

A generic public example is:

```text
/srv/jellyfin/config
/srv/jellyfin/cache
```

These paths represent fast local storage in the public example.

---

## Media Storage

Large media files have different characteristics.

They are comparatively large and primarily accessed sequentially.

The media library therefore remains on redundant bulk storage.

Generic example:

```text
/srv/media
```

Inside the container:

```text
/media
```

The main media mount can be kept read-only:

```text
/srv/media:/media:ro
```

This reduces the ability of the application container to modify the entire
library unintentionally.

---

## Writable Music Path

The production deployment has a specific requirement for write access to the
music tree while keeping the wider media mount read-only.

A sanitized representation is:

```text
/srv/media:/media:ro
/srv/media/Music:/media/Music:rw
```

The more specific mount provides write access only where it is required.

This is intentional and should not be removed merely because it appears to
overlap with the broader media mount.

---

## NVIDIA GPU

The container receives one NVIDIA GPU through Docker device reservations.

Generic Compose representation:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities:
            - gpu
```

The container also receives the required NVIDIA driver capabilities.

The GPU is used for media-processing workloads rather than assigning all
transcoding work to the CPU.

The validated transcoding configuration will be documented separately.

---

## Network Model

Jellyfin listens internally on:

```text
8096/tcp
```

A sanitized LAN publication example is:

```text
192.168.10.20:8096 -> container:8096
```

The application is not intended to terminate public TLS itself.

External requests instead follow:

```text
Internet
   |
   v
Reverse Proxy
   |
   v
Internal Jellyfin endpoint
```

This separates internet-facing HTTPS responsibilities from the media
application.

---

## External Access

The reverse proxy layer is responsible for:

- TLS termination;
- certificate handling;
- hostname routing;
- forwarding requests to Jellyfin.

Dynamic DNS is used when the internet connection has a changing public address.

Those components will be documented separately because they represent distinct
infrastructure layers.

---

## Backup Model

Jellyfin application state requires backup because it contains persistent
configuration and database information.

Cache is treated differently because it is rebuildable.

The architecture therefore distinguishes:

```text
Persistent application state -> backup required
Cache/transcode data          -> rebuildable
Media library                 -> separate storage strategy
```

The production backup workflow also considers application consistency during
backup operations.

That process will be documented in a dedicated backup section.

---

## Design Principles

The deployment follows these principles:

### Separate workloads

```text
Application state -> fast storage
Media             -> redundant bulk storage
```

### Minimize unnecessary write access

```text
Media root  -> read-only
Music path  -> writable only where required
```

### Use hardware where appropriate

```text
CPU
 +
NVIDIA GPU
```

### Separate internal applications from public ingress

```text
Internet
   |
Reverse Proxy
   |
Internal Service
```

### Avoid undocumented changes

Before modifying the active deployment:

```text
backup
   ->
validate configuration
   ->
change one component
   ->
verify
   ->
retain rollback path
```

---

## Public Repository Policy

The examples in this repository are deliberately sanitized.

The following are not published:

- real private addresses;
- real public addresses;
- production domain names;
- credentials;
- DDNS keys;
- tokens;
- certificate private keys;
- exact host-specific paths where disclosure is unnecessary.

The goal is to document the architecture without publishing operational
secrets.
