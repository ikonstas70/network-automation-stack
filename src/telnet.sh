#!/bin/bash
# socat Gateway — TCP relay from management host to target device
# Maps local ports 2301-2310 to corresponding Telnet ports on the target host

# Target host address (set via environment or edit here)
REMOTE_IP="${REMOTE_IP:-<target-host-ip>}"

# Get Tailscale IP for remote access mode
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)

# Ports to forward (one per CSR1000v router)
PORTS=(2301 2302 2303 2304 2305 2306 2307 2308 2309 2310)

echo "=== socat Gateway ==="
[ -n "$TAILSCALE_IP" ] && echo "Tailscale IP: $TAILSCALE_IP" || echo "Tailscale: not detected"
echo
echo "Select forwarding mode:"
echo "  1) Local only (127.0.0.1) — Flask API access only"
echo "  2) Remote access via Tailscale — private VPN access"
echo "  3) Audit — check active listeners"
read -rp "Choice [1-3]: " choice

case $choice in
    1)
        BIND_IP="127.0.0.1"
        ;;
    2)
        if [ -z "$TAILSCALE_IP" ]; then
            echo "[!] Tailscale IP not found. Is Tailscale running?"
            exit 1
        fi
        BIND_IP="$TAILSCALE_IP"
        ;;
    3)
        echo "Active socat listeners:"
        for PORT in "${PORTS[@]}"; do
            sudo lsof -nP -iTCP:$PORT -sTCP:LISTEN 2>/dev/null
        done
        exit 0
        ;;
    *)
        echo "Invalid choice."
        exit 1
        ;;
esac

# Kill any existing listeners on these ports (clean state)
echo "[*] Clearing existing listeners..."
for PORT in "${PORTS[@]}"; do
    sudo lsof -t -iTCP:$PORT -sTCP:LISTEN 2>/dev/null | xargs -r sudo kill
done

# Locate socat binary
SOCAT=$(which socat 2>/dev/null || echo "/opt/homebrew/bin/socat")
if [ ! -x "$SOCAT" ]; then
    echo "[!] socat not found. Install with: brew install socat"
    exit 1
fi

# Start forwarding
echo "[*] Starting forwards ($BIND_IP -> $REMOTE_IP)..."
for PORT in "${PORTS[@]}"; do
    echo "    $BIND_IP:$PORT -> $REMOTE_IP:$PORT"
    sudo nohup "$SOCAT" \
        TCP-LISTEN:$PORT,bind=$BIND_IP,fork \
        TCP:$REMOTE_IP:$PORT \
        > ~/socat_$PORT.log 2>&1 &
done

echo "[+] All forwards active."
echo "    Logs: ~/socat_<port>.log"
