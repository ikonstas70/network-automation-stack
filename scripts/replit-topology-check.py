"""
Replit Topology Check — Network Automation Stack
Polls all active CSR1000v routers via the Flask API gateway.

Usage:
    Set BASE_URL to your Cloudflare tunnel URL or http://127.0.0.1:8080 for local testing.
    Set API_KEY to your X-API-KEY value.
    Run: python3 replit-topology-check.py
"""

import requests
import time

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "https://YOUR-TUNNEL-URL.trycloudflare.com/telnet"
# For local testing, use:
# BASE_URL = "http://127.0.0.1:8080/telnet"

API_KEY = "YOUR_SECRET_KEY_HERE"
HEADERS = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}

# Active router ports (10-router deployment: 2301–2310)
PORTS = range(2301, 2311)

# Command to run against each router
COMMAND = "show ip interface brief"

# Delay between requests — prevents overwhelming the device Telnet buffer
REQUEST_DELAY = 1  # seconds


# ── Main ─────────────────────────────────────────────────────────────────────
def check_router(port: int) -> dict:
    """Send a command to a single router via the API gateway."""
    router_id = port - 2300
    payload = {"port": port, "command": COMMAND}

    try:
        response = requests.post(BASE_URL, json=payload, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"port": port, "router": f"R{router_id}", "output": "ERROR: Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"port": port, "router": f"R{router_id}", "output": "ERROR: Cannot reach API gateway"}
    except requests.exceptions.HTTPError as e:
        return {"port": port, "router": f"R{router_id}", "output": f"ERROR: HTTP {e.response.status_code}"}
    except Exception as e:
        return {"port": port, "router": f"R{router_id}", "output": f"ERROR: {e}"}


def main():
    print("=" * 60)
    print(" Network Automation Stack — Router Topology Check")
    print(f" Command: {COMMAND}")
    print(f" Polling {len(range(*PORTS.indices(PORTS.stop)))} routers")
    print("=" * 60)

    results = []

    for port in PORTS:
        router_id = port - 2300
        print(f"\n--- R{router_id} (Port {port}) ---")

        data = check_router(port)
        output = data.get("output", "No output received")

        print(output)
        results.append({"router": f"R{router_id}", "port": port, "output": output})

        time.sleep(REQUEST_DELAY)

    # Summary
    print("\n" + "=" * 60)
    reachable = [r for r in results if not r["output"].startswith("ERROR")]
    failed = [r for r in results if r["output"].startswith("ERROR")]

    print(f" Reachable: {len(reachable)} / {len(results)}")
    if failed:
        print(f" Failed:    {len(failed)}")
        for r in failed:
            print(f"   - {r['router']} (port {r['port']}): {r['output']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
