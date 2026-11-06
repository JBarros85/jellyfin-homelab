# Jellyfin External Access Failure After Public IP Change

**Incident date:** November 1, 2026

**Category:** Networking / DNS / Remote Access

**Components:** Jellyfin, Docker, Nginx Proxy Manager, No-IP, systemd

**Resolution:** Automated Dynamic DNS updates using No-IP DUC 3.3.0

## 1. Problem

Jellyfin became inaccessible through its external HTTPS hostname.

The service continued working normally inside the local network.

The initial symptoms could have indicated a problem with:

- Jellyfin itself;
- Docker networking;
- Nginx Proxy Manager;
- router port forwarding;
- the internet connection;
- DNS resolution.

The investigation identified a DNS-related connectivity failure.

## 2. Environment

The deployment uses the following architecture:

```text
Remote Client
      |
      v
Dynamic DNS Hostname
      |
      v
Public Internet IP
      |
      v
Router / TCP 443
      |
      v
Nginx Proxy Manager
      |
      v
Jellyfin Docker Container
      |
      v
Internal TCP 8096
```

Relevant components:

| Component | Technology |
| --- | --- |
| Media server | Jellyfin 12.4 |
| Container platform | Docker |
| Reverse proxy | Nginx Proxy Manager |
| External transport | HTTPS |
| Dynamic DNS provider | No-IP |
| Service management | systemd |
| Operating system | Ubuntu Linux |

Production domains and IP addresses are omitted.

## 3. Symptoms

External access to Jellyfin stopped working.

However, local checks showed:

```text
Jellyfin container: Healthy
Jellyfin LAN access: Working
Reverse proxy: Running
HTTP/HTTPS ports: Listening
External hostname: Not working
```

The application was available internally.

This suggested that the failure occurred somewhere along the
external connectivity path.

## 4. Initial Investigation

### Check Docker

The first step was to verify the Jellyfin container.

```bash
docker ps --filter name=jellyfin
```

Jellyfin was running and healthy.

### Check local connectivity

A direct HTTP request to Jellyfin's internal endpoint worked.

Generic example:

```bash
curl -I http://<LAN_IP>:8096/
```

The local application was operational.

### Check reverse proxy

Nginx Proxy Manager was running.

The expected HTTP and HTTPS ports were listening.

```bash
sudo ss -lntp | grep -E ':(80|443)[[:space:]]'
```

There was no evidence at this stage that Jellyfin needed
to be restarted or recreated.

## 5. DNS Investigation

The next step was to compare two values:

1. The server's current public IPv4 address.
2. The address returned by the Dynamic DNS hostname.

### Current public IP

```bash
curl -4 -s https://ifconfig.me
```

### DNS resolution

```bash
getent ahostsv4 <DDNS_HOSTNAME>
```

The comparison revealed a mismatch.

```text
Current public IP:  NEW_IP

DDNS A record:      OLD_IP

Result:             MISMATCH
```

The hostname was resolving to an address that no longer
represented the current internet connection.

## 6. Root Cause

The internet service provider had assigned a new public IP.

The No-IP hostname still pointed to the previous address.

There was no active Dynamic DNS updater maintaining the
record automatically at the time of the incident.

Consequently:

```text
External Client
      |
      v
DDNS Hostname
      |
      v
Old Public IP
      |
      X
Current Router
```

Traffic was directed to the wrong public address.

The failure occurred before requests could reach the
working Jellyfin service.

## 7. Resolution

The official No-IP Dynamic Update Client was installed.

Version:

```text
No-IP DUC 3.3.0
```

The client was configured with a dedicated DDNS Key.

It runs as a native systemd service:

```text
noip-duc.service
```

Relevant operational locations:

```text
/usr/bin/noip-duc
/etc/default/noip-duc
```

The configuration contains sensitive authentication
information and must never be committed to Git.

The service was enabled to start automatically with
the operating system.

## 8. systemd Integration

The running service can be verified with:

```bash
systemctl is-active noip-duc
```

Automatic startup can be checked with:

```bash
systemctl is-enabled noip-duc
```

Expected results:

```text
active
enabled
```

Recent service events can be inspected with:

```bash
journalctl -u noip-duc -n 30 --no-pager
```

During the incident, the DUC reported a successful
Dynamic DNS update.

## 9. Verification After the Fix

The public IP address was compared with the resolved
DNS address again.

After the update:

```text
Current public IP:  NEW_IP

DDNS A record:      NEW_IP

Result:             MATCH
```

A reusable verification command is:

```bash
PUBLIC_IP=$(curl -4 -s https://ifconfig.me)

DNS_IP=$(getent ahostsv4 <DDNS_HOSTNAME> |
  awk 'NR==1 {print $1}')

if [ -n "$PUBLIC_IP" ] &&
   [ "$PUBLIC_IP" = "$DNS_IP" ]; then
    echo "DNS matches public IP"
else
    echo "DNS mismatch or lookup failure"
fi
```

This confirms DNS consistency at the time of testing.

## 10. HTTPS Recovery

After correcting the DNS record, the configured
HTTPS hostname responded again.

The recovery validation included:

```bash
curl -I https://<DDNS_HOSTNAME>
```

An HTTP redirect response was received through the
HTTPS endpoint.

This showed that requests were again reaching
the configured reverse proxy.

A test from a different external network provides
stronger confirmation of end-to-end remote access.

## 11. Why Restarting Jellyfin Was Unnecessary

The Jellyfin service was already healthy.

The application responded correctly within the LAN.

Restarting Jellyfin would not have changed the
incorrect DNS record.

The incident illustrates the importance of separating:

```text
Application Availability
          |
          v
Internal Network Availability
          |
          v
External Network Connectivity
          |
          v
DNS Resolution
```

Each layer should be tested independently.

## 12. Preventive Improvement

Before the incident:

```text
Public IP changes
       |
       v
DNS record becomes outdated
       |
       v
External access fails
```

After implementing No-IP DUC:

```text
Public IP changes
       |
       v
No-IP DUC detects the change
       |
       v
DDNS record is updated
       |
       v
Hostname resolves to current IP
```

The important improvement was automation.

Manual DNS correction alone would not have prevented
the same failure from happening again.

## 13. Troubleshooting Checklist

When Jellyfin becomes inaccessible externally:

1. Verify the Jellyfin container is running.
2. Test Jellyfin directly through the LAN.
3. Check Nginx Proxy Manager.
4. Confirm that ports 80/443 are listening.
5. Retrieve the current public IPv4 address.
6. Resolve the configured DDNS hostname.
7. Compare both addresses.
8. Inspect the No-IP DUC service and logs.
9. Test HTTPS using the configured hostname.
10. Confirm access from a separate external network.

Do not restart containers or change router rules
without evidence that they are involved.

## 14. Security

Never publish:

- actual DDNS hostnames;
- public IP addresses;
- private network addresses;
- DDNS Keys;
- passwords;
- API tokens;
- reverse proxy credentials.

This incident report uses placeholders.

Production configuration files are deliberately
excluded from the repository.

## 15. Lessons Learned

The outage was not caused by Jellyfin.

The service and reverse proxy were operating normally.

The root cause was an outdated Dynamic DNS record
after a public IP change.

The incident demonstrated:

- systematic layered troubleshooting;
- Docker service verification;
- DNS diagnosis;
- reverse proxy validation;
- systemd service management;
- automation of a recurring operational dependency.

## Final Result

```text
Jellyfin LAN:          Working
Reverse Proxy:         Working
No-IP DUC:             Installed
No-IP Service:         Active
Automatic Startup:     Enabled
Public IP / DNS:       Matching
External HTTPS:        Restored
```

The permanent improvement was automated Dynamic DNS
maintenance using No-IP DUC 3.3.0.
