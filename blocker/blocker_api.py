"""
==============================================
  BLOCKER API — Microservicio de bloqueo SOAR
==============================================
Expone endpoints HTTP para que n8n aplique
reglas de firewall reales en el host Windows.

Requiere ejecutarse como Administrador.
Puerto: 8765
"""
import subprocess
import platform
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "superpoderosas26"
RULE_PREFIX = "SIEM_BLOCK_"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("blocker_api.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("blocker_api")

IS_WINDOWS = platform.system() == "Windows"


# ── Firewall helpers ──────────────────────────────────────────────────────────

def _run(cmd: str):
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def apply_block(ip: str):
    rule = f"{RULE_PREFIX}{ip}"
    if IS_WINDOWS:
        ok, msg = _run(
            f'netsh advfirewall firewall add rule '
            f'name="{rule}" dir=in action=block remoteip={ip} enable=yes'
        )
    else:
        # Linux fallback
        ok, msg = _run(f"iptables -A INPUT -s {ip} -j DROP")
    return ok, msg, rule


def remove_block(ip: str):
    rule = f"{RULE_PREFIX}{ip}"
    if IS_WINDOWS:
        ok, msg = _run(f'netsh advfirewall firewall delete rule name="{rule}"')
    else:
        ok, msg = _run(f"iptables -D INPUT -s {ip} -j DROP")
    return ok, msg


def list_rules():
    if IS_WINDOWS:
        _, out = _run(
            f'netsh advfirewall firewall show rule name=all dir=in'
        )
        lines = [l for l in out.splitlines() if RULE_PREFIX in l or "Rule Name" in l]
        return lines
    else:
        _, out = _run(f"iptables -L INPUT -n | grep DROP")
        return out.splitlines()


# ── Auth ──────────────────────────────────────────────────────────────────────

def check_auth():
    return request.headers.get("x-siem-key") == API_KEY


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "platform": platform.system()})


@app.route("/block", methods=["POST"])
def block():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ip = data.get("ip", "").strip()
    reason = data.get("reason", "SOAR auto-block")

    if not ip:
        return jsonify({"error": "Campo 'ip' requerido"}), 400

    log.info("BLOCK request: ip=%s reason=%s", ip, reason)
    ok, msg, rule = apply_block(ip)
    log.info("BLOCK result: ok=%s msg=%s", ok, msg)

    return jsonify({
        "success": ok,
        "ip": ip,
        "rule_name": rule,
        "message": msg,
        "reason": reason,
    }), 200 if ok else 500


@app.route("/unblock", methods=["POST"])
def unblock():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ip = data.get("ip", "").strip()

    if not ip:
        return jsonify({"error": "Campo 'ip' requerido"}), 400

    log.info("UNBLOCK request: ip=%s", ip)
    ok, msg = remove_block(ip)
    log.info("UNBLOCK result: ok=%s msg=%s", ok, msg)

    return jsonify({"success": ok, "ip": ip, "message": msg}), 200 if ok else 500


@app.route("/rules", methods=["GET"])
def rules():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    lines = list_rules()
    return jsonify({"rules": lines, "count": len(lines)})


if __name__ == "__main__":
    log.info("=== Blocker API iniciando en puerto 8765 ===")
    log.info("Plataforma: %s", platform.system())
    app.run(host="0.0.0.0", port=8765, debug=False)
