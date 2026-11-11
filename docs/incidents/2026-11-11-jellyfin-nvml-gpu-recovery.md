# Jellyfin GPU Access Failure: NVML Unknown Error

**Incident date:** November 11, 2026

**Status:** Resolved and validated

**Category:** Docker / NVIDIA / GPU Troubleshooting

## 1. Incident Summary

During a routine audit, a Docker-based Jellyfin instance
was found to have lost access to its NVIDIA GPU.

The container remained running and reported a healthy state.

However, executing:

```bash
docker exec jellyfin nvidia-smi
```

returned:

```text
Failed to initialize NVML: Unknown Error
```

The NVIDIA GPU remained operational on the Ubuntu host
and inside another GPU-enabled container.

The issue was isolated to the Jellyfin container.

**Resolution:** Recreate only the affected Jellyfin container
using the existing Docker Compose configuration.

After recreation, NVIDIA access was restored and GPU usage
was validated during a real Jellyfin playback session.

## 2. Environment

| Component | Configuration |
| --- | --- |
| Operating system | Ubuntu Linux |
| GPU | NVIDIA GeForce RTX 5060 Ti 16 GB |
| NVIDIA driver | 580.178.04 |
| Reported CUDA version | 13.0 |
| Docker Engine | 29.1.3 |
| NVIDIA Container Toolkit | 1.20.1 |
| Cgroup driver | systemd |
| Cgroup version | 2 |
| Container runtime | runc |
| Jellyfin | 12.4.0 |
| Container orchestration | Docker Compose |

The server runs multiple Docker services, so recovery
operations needed to avoid disrupting unrelated containers.

Production hostnames, network addresses and private
configuration paths are intentionally omitted.

## 3. Initial Symptoms

The following observations were recorded:

```text
Ubuntu host GPU access:       Working
Another GPU container:        Working
Jellyfin container state:     Healthy
Jellyfin NVIDIA NVML access:  Failed
```

This showed that Docker health reporting alone was
insufficient to confirm hardware acceleration availability.

The problem was not a complete host GPU outage.

## 4. Diagnostic Investigation

### 4.1 Verify GPU Access on the Host

```bash
nvidia-smi
```

Result:

```text
NVIDIA RTX 5060 Ti detected successfully
```

The host driver was operational.

### 4.2 Compare Another GPU Container

The same NVIDIA management command worked inside
another GPU-enabled Docker container.

This helped narrow the failure to the affected container,
rather than the host-wide NVIDIA installation.

### 4.3 Inspect Docker GPU Requests

```bash
docker inspect jellyfin --format \
'{{json .HostConfig.DeviceRequests}}'
```

The relevant configuration included:

```json
{
  "Driver": "nvidia",
  "Count": 1,
  "Capabilities": [["gpu"]]
}
```

The container was configured to request an NVIDIA GPU.

### 4.4 Inspect GPU Devices

```bash
docker exec jellyfin sh -c \
'ls -l /dev/nvidia*'
```

Devices were present, including:

```text
/dev/nvidia0
/dev/nvidiactl
/dev/nvidia-uvm
/dev/nvidia-uvm-tools
/dev/nvidia-modeset
```

NVIDIA shared libraries were also present:

```text
libnvidia-ml.so.1
libcuda.so.1
```

Despite these resources being visible, NVML initialization
still failed.

**Key finding:** GPU device visibility does not guarantee
that a running container can successfully use the GPU.

## 5. Possible Root Cause

NVIDIA documents cases where running containers lose GPU
access following certain cgroup or systemd interactions.

The affected environment used:

```text
Cgroup driver: systemd
Cgroup version: 2
Runtime: runc
```

Possible mechanisms discussed in NVIDIA documentation
include changes to device permissions or resource
associations after container creation.

The observations were compatible with this class
of issue:

- The host GPU continued working.
- Another container could access the GPU.
- Jellyfin could see NVIDIA devices and libraries.
- Jellyfin could not initialize NVML.
- Recreating Jellyfin immediately restored access.

However, the investigation did not establish that a
specific systemd reload, cgroup change or runtime
operation caused this incident.

**The exact root cause remains unconfirmed.**

## 6. Recovery Procedure

The recovery was limited to the affected Docker service.

No global Docker restart, host reboot or driver
reinstallation was necessary.

### 6.1 Pre-Recovery Safety Checks

Before recreating a production container:

1. Identify the correct Compose project and service.
2. Confirm the current image and GPU configuration.
3. Inspect persistent bind mounts and volumes.
4. Confirm that application data is backed up.
5. Preserve a copy of the Compose configuration.
6. Confirm that a brief Jellyfin interruption is acceptable.

Data stored only in a container's writable layer may be
lost when it is recreated.

### 6.2 Validate Docker Compose

Run these commands from the actual Compose project
directory:

```bash
docker compose config -q
```

The configuration must validate successfully before
any service recreation.

### 6.3 Back Up the Compose File

Example, using a verified Compose filename:

```bash
cp -p docker-compose.yml \
  "docker-compose.yml.bak-$(date +%Y%m%d-%H%M%S)"
```

A Compose file backup does not replace a backup of
persistent application data.

### 6.4 Recreate Only Jellyfin

The successful recovery operation was:

```bash
docker compose up -d \
  --no-deps \
  --no-build \
  --pull never \
  --force-recreate \
  jellyfin
```

**Warning:** This operation temporarily interrupts Jellyfin.

It must only be used after validating persistent storage,
the Compose project and the service configuration.

Parameter explanation:

| Option | Purpose |
| --- | --- |
| `-d` | Run in the background |
| `--no-deps` | Do not start dependencies |
| `--no-build` | Do not rebuild images |
| `--pull never` | Do not download images |
| `--force-recreate` | Recreate the container |
| `jellyfin` | Target only this service |

The existing persistent mounts were preserved.

No unrelated container was recreated.

## 7. Post-Recovery Validation

### 7.1 NVIDIA Access

```bash
docker exec jellyfin nvidia-smi
```

Result:

```text
GPU: NVIDIA GeForce RTX 5060 Ti
Driver: 580.178.04
CUDA: 13.0
```

The original NVML failure was no longer present.

### 7.2 Jellyfin Health

```bash
docker inspect jellyfin --format \
'Status={{.State.Status}} Health={{.State.Health.Status}}'
```

Result:

```text
Status=running Health=healthy
```

### 7.3 Recent Error Logs

A short post-recovery inspection was performed:

```bash
docker logs jellyfin --since 2m 2>&1 |
grep -Ei '\[ERR\]|\[FTL\]|exception' |
tail -15
```

No matching entries appeared during that brief interval.

This does not establish that all historical or future
application errors have been resolved.

## 8. Real GPU Workload Test

A functional playback test was conducted after recovery.

Test procedure:

1. Play a 4K video in Jellyfin.
2. Manually reduce playback quality to 720p.
3. Observe GPU activity using:

```bash
watch -n 1 nvidia-smi
```

Recorded observations:

| Metric | Result |
| --- | --- |
| GPU | NVIDIA RTX 5060 Ti |
| Temperature | 40 C |
| Power consumption | 52 W |
| GPU utilization | 13% |
| Total allocated VRAM | 1628 MiB |
| FFmpeg process VRAM | 959 MiB |

The active GPU process was:

```text
/usr/lib/jellyfin-ffmpeg/ffmpeg
```

This confirmed that FFmpeg was successfully accessing
GPU resources during the playback test.

The test did not independently identify the exact
encoder or decoder used.

Specific verification of NVENC, NVDEC and HDR tone
mapping requires the corresponding transcoding logs.

## 9. Changes That Were Not Necessary

The following actions were avoided:

- Rebooting Ubuntu.
- Restarting the global Docker daemon.
- Reinstalling NVIDIA drivers.
- Reinstalling NVIDIA Container Toolkit.
- Changing host cgroup configuration.
- Recreating unrelated containers.
- Reinstalling Jellyfin.
- Deleting persistent libraries or databases.

This reduced unnecessary operational risk.

## 10. Prevention and Monitoring

Future GPU-related incidents should be investigated
layer by layer:

```text
Host GPU
   |
   v
Other GPU-enabled containers
   |
   v
Affected container GPU request
   |
   v
NVIDIA devices and libraries
   |
   v
NVML functionality
   |
   v
Real application workload
```

Suggested checks:

```bash
nvidia-smi
```

```bash
docker exec jellyfin nvidia-smi
```

```bash
docker inspect jellyfin --format \
'{{json .HostConfig.DeviceRequests}}'
```

A container can be healthy while a GPU dependency
is not operational.

Therefore, GPU-dependent services benefit from
explicit GPU availability checks.

NVIDIA also documents alternative GPU integration
approaches, including Container Device Interface (CDI).

Such changes must be evaluated carefully before
modifying a production Docker environment.

## 11. Lessons Learned

- Docker health checks do not validate every dependency.
- NVIDIA device nodes may remain visible while GPU access fails.
- Host GPU health should be tested separately.
- Comparing containers can help isolate the failure.
- Recreating one affected service can restore GPU access.
- Persistent data and Compose configuration must be checked first.
- Recovery success does not prove the original root cause.
- Real playback testing is stronger than checking device visibility alone.

## 12. Final Outcome

```text
Jellyfin running:             YES
Jellyfin healthy:             YES
NVIDIA NVML access:           RESTORED
Host GPU access:              WORKING
Other GPU containers:         UNAFFECTED
FFmpeg GPU activity:          CONFIRMED
Global Docker restart:        NOT REQUIRED
Ubuntu reboot:                NOT REQUIRED
```

The isolated Jellyfin container recreation successfully
restored NVIDIA GPU access.

This case demonstrates a low-impact recovery approach
for a GPU access failure in a multi-service Docker host.

The original triggering event remains unidentified.

## References

- [NVIDIA Container Toolkit - Troubleshooting](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/troubleshooting.html)
- [NVIDIA - Containers Losing GPU Access](https://github.com/NVIDIA/nvidia-docker/issues/1730)
- [NVIDIA Container Toolkit - Issue 1744](https://github.com/NVIDIA/nvidia-container-toolkit/issues/1744)
- [Jellyfin Hardware Acceleration Documentation](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/)

**Validated on November 11, 2026.**
