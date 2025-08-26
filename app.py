import hmac
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# In-memory 'DB' for demo purposes
SESSIONS = {}
RESULTS = {}

SHARED_SECRET = os.getenv("WEBHOOK_SHARED_SECRET", "")

def verify_signature(raw_body: bytes, header_sig: str, secret: str) -> bool:
    if not header_sig or not secret:
        return False
    try:
        if header_sig.startswith("sha256=") or header_sig.startswith("sha256:"):
            header_sig = header_sig.split("=", 1)[-1] if "=" in header_sig else header_sig.split(":", 1)[-1]
        computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, header_sig)
    except Exception:
        return False

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify(ok=True, msg="pong"), 200

# --- Create Session ---
@app.route("/sessions", methods=["POST"])
def create_session():
    # Creates a mock age verification session.
    now = datetime.now(timezone.utc)
    body = request.get_json(silent=True) or {}
    session_id = str(uuid.uuid4())

    session = {
        "id": session_id,
        "created_at": now.isoformat(),
        "status": "created",
        "policy": body.get("policy", {"age_threshold": 18, "type": "age_over"}),
        "reference": body.get("reference"),
        "callback_url": body.get("callback_url"),
        "ttl_seconds": 900,
        "expires_at": (now + timedelta(seconds=900)).isoformat()
    }
    SESSIONS[session_id] = session

    # Pre-generate a canned result for this session
    result = {
        "session_id": session_id,
        "status": "pending",
        "outcome": None,
        "reason": None,
        "attributes": {
            "age_over": True,
            "age_threshold": session["policy"]["age_threshold"]
        }
    }
    RESULTS[session_id] = result

    return jsonify({"session": session}), 201

# --- Retrieve Result ---
@app.route("/sessions/<session_id>/result", methods=["GET"])
def get_result(session_id):
    res = RESULTS.get(session_id)
    if not res:
        return jsonify({"error": "not_found", "message": "Unknown session id"}), 404
    return jsonify({"result": res}), 200

# --- Webhook Notification ---
@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data()
    signature = request.headers.get("X-Signature", "")

    verified = verify_signature(raw, signature, SHARED_SECRET) if SHARED_SECRET else None
    payload = request.get_json(silent=True) or {}

    # Accept an event that marks a session complete.
    if payload.get("event") == "verification_complete" and payload.get("session_id") in RESULTS:
        sid = payload["session_id"]
        approved = bool(payload.get("approved", True))
        RESULTS[sid]["status"] = "complete"
        RESULTS[sid]["outcome"] = "approved" if approved else "rejected"
        RESULTS[sid]["reason"] = payload.get("reason")

        if sid in SESSIONS:
            SESSIONS[sid]["status"] = "complete"

    res = {
        "received": True,
        "verified": verified,
        "json": payload,
    }
    return jsonify(res), 200

# --- Serve OpenAPI spec ---
@app.route("/openapi.yaml", methods=["GET"])
def serve_openapi():
    return send_from_directory(".", "openapi.yaml", mimetype="text/yaml")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
