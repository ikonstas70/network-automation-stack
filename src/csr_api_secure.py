import argparse
import os
import re
import subprocess

from flask import Flask, request, jsonify

app = Flask(__name__)

ALLOWED_PORTS = list(range(2301, 2311))  # 10-router deployment: 2301-2310
API_KEY = os.environ.get("CSR_API_KEY", "YOUR_SECRET_KEY_HERE")
ROUTER_IP = os.environ.get("ROUTER_IP", "127.0.0.1")


def scrub_output(text):
    """Strip Telnet connection banners and terminal control codes."""
    text = re.sub(r'Trying [\d\.]+.*\n', '', text)
    text = re.sub(r'Connected to .*\n', '', text)
    text = re.sub(r'Escape character is.*\n', '', text)
    return text.strip()


@app.route("/telnet", methods=["POST"])
def telnet_router():
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    port = data.get("port")
    command = data.get("command", "").strip()

    if port not in ALLOWED_PORTS:
        return jsonify({"error": "Port not allowed"}), 400

    try:
        # Timed sequence required for Telnet/serial buffer stability:
        # Connect -> Sleep -> Wake -> Sleep -> Execute -> Sleep -> Exit
        shell_cmd = (
            f'(sleep 1; printf "\\r\\n"; sleep 1; '
            f'printf "terminal length 0\\r\\n"; sleep 1; '
            f'printf "{command}\\r\\n"; sleep 2; '
            f'printf "exit\\r\\n") | telnet {ROUTER_IP} {port}'
        )

        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            shell=True,       # NOTE: shell=True required for timed subshell pipeline.
            timeout=25        # Future: add command sanitization before production use.
        )

        return jsonify({
            "port": port,
            "router": f"R{int(port) - 2300}",
            "output": scrub_output(result.stdout + result.stderr)
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSR1000v Flask API Gateway")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port)
