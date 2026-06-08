# Network Automation Stack
### Programmatic HTTP-to-Telnet Gateway for Network Device Fleets

**Prepared by:** Network Engineering Division — IT Solutions USA  
**Date:** February 17, 2026  
**Status:** Functional & Secure

---

This project establishes a high-security, automated management layer for network device fleets. By layering a Flask API Gateway over a socat transport bridge, it converts any Telnet-accessible device into a RESTful endpoint — transforming 10–20 Cisco CSR1000v routers into a programmatically managed fleet with zero external exposure.

> **Platform-agnostic:** No hypervisor required. The stack works with any appliance reachable via Telnet on a forwarded port — physical hardware, virtual machines, console servers, or any platform that maps devices to TCP ports.

---

## Architecture Overview

```
  curl / Replit / AI Agent / Automation Script
                        |
               HTTPS (outbound-only)
                        |
            +-----------+-----------+
            |    Cloudflare Edge    |  WAF + Zero Trust
            +-----------+-----------+
                        |
                Cloudflare Tunnel
                        |
                        v
  +-----------------------------------------------------+
  |  MAC MINI  (Management Host)                        |
  |                                                     |
  |     +---------------+----------------+              |
  |     |  Flask API  :8080              |              |
  |     |  csr_api_secure.py             |              |
  |     |   - X-API-KEY validation       |              |
  |     |   - ALLOWED_PORTS check        |              |
  |     |   - Timing controller          |              |
  |     |   - scrub_output() regex       |              |
  |     +---------------+----------------+              |
  |                     |  localhost                    |
  |     +---------------+----------------+              |
  |     |  socat Gateway  (telnet.sh)    |              |
  |     |  Ports 2301-2310               |              |
  |     |   - fork  (concurrent)         |              |
  |     |   - nohup (persistent)         |              |
  |     +---------------+----------------+              |
  |                     |  L3 Point-to-Point            |
  +---------------------+-------------------------------+
                        |  (No default gateway)
                        v
  +-----------------------------------------------------+
  |  NETWORK DEVICE LAYER                               |
  |  (any Telnet-accessible appliance)                  |
  |                                                     |
  |  +------+ +------+ +------+ +------+   +------+    |
  |  |  R1  | |  R2  | |  R3  | |  R4  |...| R10  |   |
  |  | 2301 | | 2302 | | 2303 | | 2304 |   | 2310 |   |
  |  +------+ +------+ +------+ +------+   +------+    |
  |         Cisco CSR1000v Fleet (current)              |
  +-----------------------------------------------------+

  OUT-OF-BAND ACCESS (Tailscale WireGuard):
  [ Engineer ] ----------------------------------------> [ Mac Mini :2301-2310 ]
```

---

## Data Flow

```
  1. Trigger    → curl POST /telnet  {"port": 2301, "command": "show ip int brief"}
  2. Ingress    → Cloudflare Tunnel forwards to localhost:8080
  3. Validate   → Flask checks X-API-KEY + ALLOWED_PORTS
  4. Execute    → Python subshell with timed printf/telnet sequence
  5. Relay      → socat forwards localhost:2301 → <target-host>:2301
  6. Execution  → Device receives command via Telnet on the forwarded port
  7. Return     → Output scrubbed, returned as structured JSON
```

---

## Stack Components

| Layer | Component | Role |
|---|---|---|
| Edge | Cloudflare Tunnel (`cloudflared`) | Global HTTPS access, WAF, Zero Trust |
| Logic | Flask API (`csr_api_secure.py`) | Auth, port validation, timing control |
| Transport | socat Gateway (`telnet.sh`) | TCP relay: management host → target device |
| Execution | Any Telnet-accessible device | Command execution on forwarded port |
| Private Mesh | Tailscale / WireGuard | Out-of-band engineering access |

---

## Security Posture

| Feature | Mechanism | Purpose |
|---|---|---|
| Authentication | `X-API-KEY` header | Blocks unauthenticated API access |
| Port restriction | `ALLOWED_PORTS` list | Limits access to configured ports only (default: 2301–2310) |
| Network isolation | L3 Point-to-Point, no default gateway | Devices cannot be reached from internet |
| Output sanitization | `scrub_output()` regex | Strips Telnet banners and escape chars |
| Transport encryption | Tailscale WireGuard | Private mesh VPN for engineer access |
| Application firewall | Cloudflare WAF | Filters malicious inbound requests |

**Defense-in-depth:** Two independent access paths — Cloudflare (public API) and Tailscale (private console) — operate at different stack layers and do not share configuration.

> **Security Note:** The current stack uses `shell=True` for subprocess execution. Future iterations should implement command sanitization to prevent shell injection via the printf buffer.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ROUTER_IP` | IP address of the target host where devices are reachable via Telnet | `127.0.0.1` |
| `CSR_API_KEY` | Secret key required in the `X-API-KEY` header | `YOUR_SECRET_KEY_HERE` |

Set them before starting the API:

```bash
export ROUTER_IP="<target-host-ip>"
export CSR_API_KEY="your-secret-key"
```

Or create a `.env` file (never commit this):

```bash
ROUTER_IP=<target-host-ip>
CSR_API_KEY=your-secret-key
```

---

## Quick Start

```bash
# 0. Install dependencies
python3 -m venv ~/csr_env && source ~/csr_env/bin/activate
pip install -r requirements.txt

# 1. Start the socat transport bridge
sh src/telnet.sh
# Select mode: 1 (local only) or 2 (Tailscale)

# 2. Start the Flask API
sh src/start_csr_api.sh

# 3. Open the Cloudflare tunnel (keep terminal open)
cloudflared tunnel --url http://localhost:8080

# 4. Send a command to a router
curl -X POST http://127.0.0.1:8080/telnet \
     -H "X-API-KEY: YOUR_SECRET_KEY_HERE" \
     -H "Content-Type: application/json" \
     -d '{"port": 2301, "command": "show ip interface brief"}'
```

---

## Repository Contents

| Path | Description |
|---|---|
| [`docs/technical-report.md`](docs/technical-report.md) | Full technical report with implementation detail |
| [`ROADMAP.md`](ROADMAP.md) | Phase 2 platform roadmap — Netmiko, NAPALM, Nornir, NetworkX, Scapy, Nginx SSL |
| [`scripts/replit-topology-check.py`](scripts/replit-topology-check.py) | Python script to poll all 10 routers via the API |

---

## Future Roadmap

- Command sanitization to replace `shell=True` subprocess execution
- SSH transport layer replacing Telnet over socat
- Self-hosted LLM integration for AI-driven network operations
- NAPALM / Ansible orchestration layer over the Flask API
- Persistent Cloudflare named tunnel (replacing quick tunnels)
