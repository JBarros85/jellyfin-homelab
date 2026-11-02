# NVIDIA Hardware Transcoding

This Jellyfin deployment uses an NVIDIA GPU to accelerate video decoding,
processing and encoding.

The goal is to move supported media-processing workloads away from the CPU and
onto dedicated GPU hardware.

---

## Audited Environment

The current validated environment uses:

```text
Jellyfin:           12.4
GPU:                NVIDIA GeForce RTX 5060 Ti
GPU memory:         16311 MiB
NVIDIA driver:      580.178.04
Jellyfin FFmpeg:    8.1.3-Jellyfin
Container health:   healthy
Restart policy:     unless-stopped
```

The same NVIDIA GPU and driver version were visible both on the host and inside
the Jellyfin container.

This confirms that the container has working access to the host GPU.

---

## Docker GPU Access

The Jellyfin container receives one NVIDIA GPU through Docker device
reservations.

The effective Docker configuration reported:

```text
Driver:       nvidia
Count:        1
Capabilities: gpu
```

A generic Compose representation is:

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

The deployment also exposes the required NVIDIA driver capabilities to the
container.

---

## Verifying GPU Access

The GPU can be checked on the host with:

```bash
nvidia-smi
```

The same check should also work inside the Jellyfin container:

```bash
docker exec jellyfin nvidia-smi
```

A useful validation is to compare:

```text
GPU model
driver version
GPU memory
```

between host and container.

If these differ unexpectedly, or if `nvidia-smi` fails inside the container,
hardware transcoding should not be considered operational.

---

## Jellyfin FFmpeg

Jellyfin uses its own FFmpeg build:

```text
/usr/lib/jellyfin-ffmpeg/ffmpeg
```

The audited deployment reported:

```text
ffmpeg version 8.1.3-Jellyfin
```

The build includes NVIDIA-related support such as:

```text
CUDA
NVDEC
NVENC
CUVID
```

---

## Hardware Acceleration Methods

The current FFmpeg build exposes several acceleration methods.

The relevant method for this deployment is:

```text
cuda
```

Other acceleration methods may also be present in the FFmpeg build, but the
Jellyfin configuration uses NVIDIA NVENC/CUDA.

Check available methods with:

```bash
docker exec jellyfin \
  /usr/lib/jellyfin-ffmpeg/ffmpeg -hide_banner -hwaccels
```

---

## NVIDIA Encoders

The following NVIDIA encoders were confirmed in the running Jellyfin container:

```text
h264_nvenc
hevc_nvenc
av1_nvenc
```

They can be checked with:

```bash
docker exec jellyfin sh -c '
/usr/lib/jellyfin-ffmpeg/ffmpeg -hide_banner -encoders 2>/dev/null |
grep -E "h264_nvenc|hevc_nvenc|av1_nvenc"
'
```

Their presence confirms that FFmpeg has the necessary NVIDIA encoder support.

It does not, by itself, prove that a real Jellyfin transcode is using the GPU.

For that reason, runtime validation is also required.

---

## Jellyfin Transcoding Configuration

The current Jellyfin encoding configuration includes:

```text
HardwareAccelerationType:          nvenc
EnableHardwareEncoding:            true
EnableEnhancedNvdecDecoder:        true

EnableDecodingColorDepth10Hevc:     true
EnableDecodingColorDepth10Vp9:      true
EnableDecodingColorDepth10HevcRext: true

EnableTonemapping:                  true
TonemappingAlgorithm:               bt2390
TonemappingMode:                    auto

AllowHevcEncoding:                  true
AllowAv1Encoding:                   true
```

This means Jellyfin is configured to use NVIDIA hardware acceleration where
compatible.

---

## HDR Tone Mapping Configuration

HDR to SDR tone mapping is enabled.

The configured algorithm is:

```text
BT.2390
```

The configured mode is:

```text
auto
```

This allows Jellyfin to use tone mapping when the media and playback conditions
require it.

An important distinction is:

```text
Configured feature != feature used by every transcode
```

A normal SDR transcode does not need HDR tone mapping.

Runtime FFmpeg logs should therefore be inspected when validating a specific
tone-mapping workload.

---

## Real Transcoding Validation

A recent Jellyfin transcode log confirmed actual NVIDIA usage.

The FFmpeg command contained:

```text
-init_hw_device cuda=cu:0
-filter_hw_device cu
-hwaccel cuda
-hwaccel_output_format cuda
```

This confirms that FFmpeg initialized the NVIDIA CUDA device and used CUDA for
the hardware-accelerated processing path.

The same transcode also used:

```text
scale_cuda
```

for video scaling.

---

## Hardware Encoding Validation

The recent real transcode used:

```text
h264_nvenc
```

The FFmpeg stream mapping confirmed a hardware-encoded output path.

Simplified:

```text
Input video
    |
    v
CUDA hardware acceleration
    |
    v
GPU scaling
    |
    v
h264_nvenc
    |
    v
HLS output
```

This provides stronger validation than simply checking whether the encoder is
listed by FFmpeg.

---

## Runtime Verification

A useful validation workflow is:

### 1. Force transcoding

Play media in Jellyfin and select a playback quality that requires conversion.

### 2. Find the newest FFmpeg transcode log

```bash
docker exec jellyfin sh -c '
ls -t /config/log/FFmpeg.Transcode* 2>/dev/null | head -1
'
```

### 3. Search for NVIDIA operations

```bash
docker exec jellyfin sh -c '
F=$(ls -t /config/log/FFmpeg.Transcode* 2>/dev/null | head -1)

grep -Ei \
"init_hw_device|hwaccel|scale_cuda|tonemap_cuda|nvenc|nvdec" \
"$F"
'
```

Relevant indicators include:

```text
cuda
scale_cuda
tonemap_cuda
h264_nvenc
hevc_nvenc
av1_nvenc
```

Not every transcode will contain every indicator.

The exact operations depend on the source media and requested output.

---

## GPU Process Monitoring

GPU processes can also be inspected from the host:

```bash
nvidia-smi \
  --query-compute-apps=process_name,used_memory \
  --format=csv,noheader
```

During an active hardware transcode, an FFmpeg process should normally appear
using GPU memory.

If no transcode is active, Jellyfin FFmpeg may not appear at all.

This is expected behavior.

---

## Direct Play vs Transcoding

Hardware acceleration is only relevant when Jellyfin actually needs to
transcode.

A compatible client may use:

```text
Direct Play
```

In that case:

```text
No FFmpeg transcode
No NVENC process
Minimal server processing
```

When media must be converted:

```text
Source media
    |
    v
Decode / process
    |
    v
Encode
    |
    v
Client-compatible stream
```

Hardware acceleration becomes useful during that second scenario.

---

## Validation Layers

A complete hardware-transcoding check should validate several layers.

### Layer 1 — Host

```bash
nvidia-smi
```

### Layer 2 — Container access

```bash
docker exec jellyfin nvidia-smi
```

### Layer 3 — FFmpeg capabilities

```bash
docker exec jellyfin \
  /usr/lib/jellyfin-ffmpeg/ffmpeg -hide_banner -encoders
```

### Layer 4 — Jellyfin configuration

Verify that NVIDIA acceleration and hardware encoding are enabled.

### Layer 5 — Real workload

Force a transcode and inspect the generated FFmpeg command.

Only the final layer confirms that the configured acceleration path is actually
being used during playback.

---

## Troubleshooting GPU Access

If the host can access the GPU but the container cannot:

```text
Host nvidia-smi:       OK
Container nvidia-smi:  FAIL
```

investigate:

- NVIDIA Container Toolkit;
- Docker GPU device reservation;
- container recreation after driver changes;
- compatibility between loaded kernel driver and userspace libraries.

Avoid changing Jellyfin transcoding settings until GPU access itself is
confirmed.

---

## Driver Changes

After changing or updating the NVIDIA driver, validate the GPU again before
assuming Jellyfin hardware acceleration still works.

Recommended sequence:

```text
Driver change
    |
    v
Reboot when required
    |
    v
Validate host GPU
    |
    v
Validate container GPU
    |
    v
Validate FFmpeg encoders
    |
    v
Run real transcode
```

A container created before a significant driver/runtime change may occasionally
need to be recreated so that GPU integration is initialized correctly.

---

## Privacy

Transcoding logs may expose:

- movie or episode names;
- internal media paths;
- usernames;
- filesystem layout;
- session identifiers.

Logs should therefore be sanitized before being included in a public
repository.

This repository intentionally documents only the relevant FFmpeg operations and
does not publish production media filenames.

---

## Result

The audited hardware acceleration path is:

```text
Jellyfin
   |
   v
Jellyfin FFmpeg
   |
   v
CUDA / NVIDIA
   |
   +--> hardware decode support
   +--> GPU scaling
   +--> H.264 NVENC
   +--> HEVC NVENC capability
   +--> AV1 NVENC capability
   +--> HDR tone mapping configuration
```

The current environment has been validated beyond static configuration:

```text
GPU visible inside container
        +
NVENC encoders available
        +
CUDA acceleration available
        +
real FFmpeg transcode using CUDA
        +
real hardware encoding using h264_nvenc
        =
validated NVIDIA hardware transcoding
```
