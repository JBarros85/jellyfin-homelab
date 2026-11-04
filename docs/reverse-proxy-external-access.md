# Jellyfin Reverse Proxy and HTTPS Access

This document describes the external access architecture of a
self-hosted Jellyfin deployment.

The implementation combines:

- Docker-based Jellyfin;
- Nginx Proxy Manager;
- HTTPS and TLS certificates;
- Dynamic DNS;
- private application networking;
- systemd-based DDNS automation.

## 1. Architecture

The external access path is:

```text
Remote client
     |
     v
Dynamic DNS hostname
     |
     v
Current public IP
     |
     v
Router / TCP 443
     |
     v
Nginx Proxy Manager
     |
     v
Jellyfin :8096
     |
     v
Media library
```

Jellyfin does not need to terminate public HTTPS connections
directly.

The reverse proxy provides the TLS entry point.

---

## 2. Docker Services

Two Docker services are involved in the web access path.

### Jellyfin

```text
Image:   jellyfin/jellyfin:12.4
Status:  running
Health:  healthy
Restart: unless-stopped
Port:    8096
```

### Nginx Proxy Manager

```text
Image:   jc21/nginx-proxy-manager:latest
Status:  running
Health:  healthy
Restart: unless-stopped
```

Both were operational during the audit.

---

## 3. Network Ports

Nginx Proxy Manager publishes:

| Port | Purpose |
| --- | --- |
| 80/tcp | HTTP ingress |
| 443/tcp | HTTPS ingress |
| 81/tcp | Administration interface |

Jellyfin uses port 8096 internally.

The audited proxy host was configured with:

```nginx
set $port 8096;
```

The NPM administration interface should remain accessible only
from trusted networks.

Public application access and administrative access are separate
security concerns.

---

## 4. Reverse Proxy Routing

Nginx Proxy Manager receives the external request and identifies
the configured virtual host.

A simplified request path:

```text
HTTPS request
      |
      v
Hostname / SNI matching
      |
      v
TLS termination
      |
      v
Proxy host configuration
      |
      v
Jellyfin upstream port 8096
```

During the audit, one proxy host configuration was found.

Actual domains and internal addresses are intentionally excluded
from this repository.

---

## 5. HTTP and HTTPS

The audited endpoints returned:

```text
HTTP with hostname:       301
HTTPS with hostname/SNI:  302
HTTPS through DNS:        302
```

HTTP 301 indicates a permanent redirect.

HTTPS 302 indicates a temporary redirect response after a
successful HTTPS connection.

The audit confirmed the response codes but did not inspect the
complete redirect destinations.

---

## 6. TLS and Server Name Indication

A reverse proxy can host multiple websites on the same IP address.

Server Name Indication (SNI) allows the client to specify the
intended hostname during the TLS handshake.

A test using only:

```text
https://127.0.0.1/
```

may fail because the required hostname was not supplied.

The correct test uses the intended hostname.

Example:

```bash
HOSTNAME="media.example.com"

curl --noproxy '*' \
  --resolve "$HOSTNAME:443:127.0.0.1" \
  "https://$HOSTNAME/"
```

The example hostname must be replaced with the actual configured
hostname when running the test.

This method tests the local reverse proxy while providing the
expected hostname and SNI.

---

## 7. Certificate Management

The deployment uses TLS certificates managed through
Nginx Proxy Manager.

The audited certificate validity period was:

```text
Valid from: 2026-10-13
Valid to:   2027-01-11
```

Two certificate directories were present in the certificate store.

This count does not necessarily mean both certificates are
currently assigned to active proxy hosts.

Certificate metadata can be checked with:

```bash
echo | openssl s_client \
  -connect 127.0.0.1:443 \
  -servername media.example.com 2>/dev/null |
openssl x509 -noout -dates
```

Nginx Proxy Manager also performs scheduled certificate renewal
checks.

Successful TLS access and a valid certificate do not replace
monitoring of future certificate expiry.

---

## 8. Dynamic DNS

The internet connection uses a dynamic public IP address.

Dynamic DNS provides a stable hostname even when the public IP
changes.

The system uses the official No-IP Dynamic Update Client.

```text
Service: noip-duc.service
State:   active
Startup: enabled
```

The updater runs under systemd.

This avoids depending on manual updates whenever the ISP assigns
a different public IP.

---

## 9. DNS Verification

A useful diagnostic compares the current public IPv4 address
with the resolved A record.

Example:

```bash
PUBLIC_IP="$(curl -4 -s https://ifconfig.me)"
DNS_IP="$(getent ahostsv4 media.example.com |
  awk 'NR==1 {print $1}')"

if [ "$PUBLIC_IP" = "$DNS_IP" ]; then
    echo "DDNS matches the current public IPv4 address"
else
    echo "DDNS mismatch"
fi
```

During the audit:

```text
Public IP matches DNS: YES
```

This verifies IPv4 address consistency at that moment.

IPv6 records, external DNS propagation and remote connectivity
are separate checks.

---

## 10. External HTTPS Validation

The hostname was also tested through normal DNS resolution.

Observed result:

```text
HTTPS: 302
```

This confirmed successful HTTPS access from the server using
the configured hostname.

A complete independent external-access test should also be
performed from a different network.

---

## 11. Operational Verification

### Jellyfin container

```bash
docker inspect jellyfin --format \
'{{.State.Status}}'
```

### Jellyfin health

```bash
docker inspect jellyfin --format \
'{{.State.Health.Status}}'
```

### Reverse proxy health

```bash
docker inspect npm --format \
'{{.State.Health.Status}}'
```

### NPM published ports

```bash
docker port npm
```

### No-IP service

```bash
systemctl is-active noip-duc
systemctl is-enabled noip-duc
```

### No-IP activity

```bash
journalctl -u noip-duc -n 30 --no-pager
```

Public logs must be sanitized before publication.

---

## 12. Troubleshooting Order

When external Jellyfin access fails:

```text
1. Confirm Jellyfin container health
               |
               v
2. Test Jellyfin on the LAN
               |
               v
3. Verify Nginx Proxy Manager
               |
               v
4. Check public IP and DNS resolution
               |
               v
5. Check No-IP DUC
               |
               v
6. Test HTTPS with correct hostname/SNI
               |
               v
7. Verify from an independent external network
```

This avoids unnecessary container restarts when the root cause
is outside Jellyfin.

A real Dynamic DNS incident will be documented separately
as a troubleshooting case study.

---

## 13. Security Considerations

The public documentation does not expose:

- real public IP addresses;
- actual DDNS hostname;
- LAN or VPN addresses;
- reverse proxy credentials;
- certificate private keys;
- No-IP DDNS keys;
- authentication tokens.

The NPM management interface should remain restricted to
trusted networks.

Jellyfin application traffic should use the reverse proxy
rather than unnecessarily exposing additional public ports.

---

## 14. Audit Summary

Audit date: November 4, 2026.

| Component | Result |
| --- | --- |
| Jellyfin | Healthy |
| Nginx Proxy Manager | Healthy |
| HTTP hostname test | 301 |
| HTTPS with SNI | 302 |
| HTTPS via DNS from host | 302 |
| No-IP DUC | Active |
| DDNS startup | Enabled |
| Public IPv4 / DNS comparison | Match |
| NPM upstream port | 8096 |
| Proxy hosts | 1 |
| TLS certificate | Valid at audit time |

The audit was read-only.

No Docker containers, proxy rules, TLS certificates or DDNS
configuration were changed during this documentation work.

## Conclusion

The Jellyfin deployment uses a layered external-access design:

```text
Dynamic DNS
     +
Reverse proxy
     +
TLS
     +
Internal Jellyfin service
     =
Centralized HTTPS access
```

The configuration was operational during the audit.

Monitoring and troubleshooting remain essential because public
IP addresses, DNS records and certificates can change over time.
