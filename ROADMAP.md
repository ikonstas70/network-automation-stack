# Platform Roadmap

**Project:** Network Automation Stack — Phase 2  
**Objective:** Evolve from a single-purpose API gateway into a full, self-hosted
network automation platform with no external cloud dependencies.

---

## Vision

The current stack solves the "last mile" problem — serial console access via a
REST API. Phase 2 transforms it into a professional-grade automation platform:
structured device interaction, parallel fleet operations, live topology graphing,
and packet-level diagnostics, all served over local HTTPS.

---

## Target Architecture

```
  [ Browser / Engineer / AI Agent ]
                  |
                  | HTTPS  (local, self-signed)
                  |
       +----------v-----------+
       |   Nginx  (SSL)       |  ← replaces Cloudflare Tunnel
       +----------+-----------+
                  |
       +----------v-----------+
       |   Flask API          |
       |                      |
       |   Netmiko  ──────────┼──► SSH / Telnet session management
       |   NAPALM   ──────────┼──► Structured multi-vendor data
       |   Nornir   ──────────┼──► Parallel fleet execution
       |   NetworkX ──────────┼──► Live topology graph
       |   Scapy    ──────────┼──► Packet crafting & analysis
       +----------+-----------+
                  |
       +----------v-----------+
       |   CSR1000v Fleet     |
       |   Ports 2301–2310    |
       +----------------------+
```

---

## Tool Integration Map

```
                        NETWORK AUTOMATION PLATFORM
  +------------------------------------------------------------------+
  |                                                                  |
  |   INPUT LAYER                                                    |
  |   +--------------------+   +--------------------+               |
  |   |  REST API  (Flask) |   |  CLI / Scripts     |               |
  |   +--------------------+   +--------------------+               |
  |              |                        |                          |
  |              +------------+-----------+                          |
  |                           |                                      |
  |   EXECUTION LAYER         |                                      |
  |   +-----------------------+-----------------------------+        |
  |   |                                                     |        |
  |   |  +------------+   +------------+   +------------+  |        |
  |   |  |  Netmiko   |   |   Nornir   |   |   NAPALM   |  |        |
  |   |  | Session Mgr|   |  Parallel  |   | Structured |  |        |
  |   |  | Prompt Det.|   |  Execution |   |    Data    |  |        |
  |   |  +-----+------+   +-----+------+   +-----+------+  |        |
  |   |        |                |                 |          |        |
  |   +--------+-----------------+-----------------+---------+        |
  |            |                                   |                  |
  |   ANALYSIS LAYER          |                    |                  |
  |   +------------------------+----+   +----------+-------+          |
  |   |       NetworkX              |   |      Scapy       |          |
  |   |  Topology  |  Path Analysis |   | Packet | Traffic |          |
  |   |  Graphing  |  Centrality    |   | Craft  | Capture |          |
  |   +----------------------------+   +------------------+          |
  |                                                                  |
  |   TRANSPORT LAYER                                                |
  |   +--------------------------------------------------------------+|
  |   |              socat  (TCP relay)                              ||
  |   |   Port 2301  Port 2302  Port 2303  ...  Port 2310           ||
  |   +--------------------------------------------------------------+|
  |                                                                  |
  |   DEVICE LAYER                                                   |
  |   +--------------------------------------------------------------+|
  |   |   R1      R2      R3      R4      R5   ...   R10            ||
  |   |   Cisco CSR1000v Fleet  (any Telnet-accessible appliance)   ||
  |   +--------------------------------------------------------------+|
  |                                                                  |
  +------------------------------------------------------------------+
```

---

## Data Flow by Operation Type

```
  COMMAND EXECUTION          TOPOLOGY QUERY            PACKET TEST
  ─────────────────          ──────────────            ───────────
  Client                     Client                    Client
    │                          │                         │
    │ POST /command             │ GET /topology            │ POST /probe
    ▼                          ▼                         ▼
  Flask                      Flask                     Flask
    │                          │                         │
    │ Netmiko                   │ NAPALM                   │ Scapy
    │ (prompt detect)           │ (get_interfaces)         │ (sr1)
    ▼                          ▼                         ▼
  Router                     Router                    Router
    │                          │                         │
    │ IOS output                │ Structured dict          │ ICMP reply
    ▼                          ▼                         ▼
  scrub + JSON               NetworkX                  RTT + TTL
  response                   graph update              response
```

---

## Tool Reference

### Netmiko — Session Management

Replaces the current `shell=True` subshell with a structured connection handler.
Handles prompt detection, output parsing, and timing natively — eliminating fixed
`sleep` delays and the shell injection risk in the current implementation.

```python
from netmiko import ConnectHandler

device = {
    "device_type": "cisco_ios_telnet",
    "host": "127.0.0.1",
    "port": 2301,
}

with ConnectHandler(**device) as conn:
    output = conn.send_command("show ip interface brief")
    print(output)
```

> **Priority: High** — This is the most impactful single change to the codebase.

---

### Nornir — Parallel Fleet Execution

Runs tasks across all 10 routers simultaneously. A fleet-wide poll that currently
takes 40+ seconds sequentially completes in under 5 seconds with Nornir.

```python
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="config.yaml")
result = nr.run(
    task=netmiko_send_command,
    command_string="show ip interface brief"
)
print_result(result)
```

> **Priority: High** — Directly resolves the fleet polling performance issue.

---

### NAPALM — Multi-Vendor Abstraction

Provides a unified API for retrieving structured data from network devices —
Python dicts instead of raw CLI text. Works on top of Netmiko for Cisco IOS.

```python
from napalm import get_network_driver

driver = get_network_driver("ios")
device = driver("127.0.0.1", "admin", "password",
                optional_args={"port": 2301})
device.open()

facts      = device.get_facts()        # hostname, vendor, model, uptime
interfaces = device.get_interfaces()   # structured interface state
bgp        = device.get_bgp_neighbors()

device.close()
```

> **Priority: Medium** — Enables structured data responses for AI and analytics integration.

---

### NetworkX — Topology Graph

Builds a live, queryable graph of the router fleet. Detects topology changes,
calculates shortest paths, and provides the data layer for visualisation and
AI-driven network analysis.

```python
import networkx as nx

G = nx.Graph()
G.add_nodes_from(["R1", "R2", "R3", "R4", "Hub"])
G.add_edges_from([
    ("Hub", "R1"), ("Hub", "R2"),
    ("Hub", "R3"), ("Hub", "R4"),
])

# Query shortest path
path = nx.shortest_path(G, source="R1", target="R4")

# Detect critical nodes (high betweenness centrality)
centrality = nx.betweenness_centrality(G)
```

> **Priority: Medium** — Foundation for topology-aware automation and AI reasoning.

---

### Scapy — Packet Analysis

Enables low-level network testing that CLI commands cannot provide — custom ICMP
probes, TCP session inspection, DSCP marking verification, and traffic capture.

```python
from scapy.all import IP, ICMP, sr1

# Custom ICMP probe with TTL tracking
packet   = IP(dst="192.168.2.1", ttl=64) / ICMP()
response = sr1(packet, timeout=2, verbose=0)

if response:
    print(f"Reply from {response.src}  TTL: {response.ttl}  "
          f"Time: {response.time:.3f}ms")
```

> **Priority: Low** — Advanced diagnostic capability, implement after core tools are stable.

---

### Nginx + Self-Signed SSL — Local HTTPS

Replaces the Cloudflare Tunnel with a self-hosted SSL termination layer.
Fully offline, no external dependency, persistent across reboots.

```nginx
server {
    listen              443 ssl;
    ssl_certificate     /etc/nginx/ssl/lab.crt;
    ssl_certificate_key /etc/nginx/ssl/lab.key;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }
}
```

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/lab.key \
  -out    /etc/nginx/ssl/lab.crt \
  -subj   "/CN=automation.lab"
```

> **Priority: Medium** — Removes the only remaining external dependency in the stack.

---

## Target Dependencies

```
flask>=2.3.0
netmiko>=4.3.0
napalm>=4.1.0
nornir>=3.4.0
nornir-netmiko>=1.0.0
nornir-utils>=0.2.0
networkx>=3.2.0
matplotlib>=3.8.0
scapy>=2.5.0
```

---

## Implementation Phases

| Phase | Deliverable | Impact |
|---|---|---|
| 1 | Netmiko replaces raw subshell | Removes shell injection risk, eliminates fixed sleeps |
| 2 | Nornir parallel fleet polling | 10× performance improvement on fleet-wide operations |
| 3 | NAPALM structured data layer | Structured JSON responses for AI and analytics |
| 4 | NetworkX topology endpoint | Live graph API for topology-aware automation |
| 5 | Scapy diagnostic module | Packet-level testing and DSCP verification |
| 6 | Nginx SSL termination | Full local HTTPS, no external dependencies |
