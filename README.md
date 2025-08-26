# Yoti-Style Age Verification Sandbox (Demo)

A minimal **simulation** of the key Age Verification API flows:
- **Create session**: `POST /sessions`
- **Retrieve result**: `GET /sessions/{id}/result`
- **Webhook notification**: `POST /webhook`
- **OpenAPI**: `/openapi.yaml`

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Optional: set WEBHOOK_SHARED_SECRET for HMAC verification

python app.py
# → http://localhost:5000
```

## Endpoints

- `GET /ping` — health
- `POST /sessions` — create a session (optionally pass `reference`, `callback_url`, `policy.age_threshold`)
- `GET /sessions/{id}/result` — fetch the mock decision (starts as `pending`)
- `POST /webhook` — mark a session complete via event

### Event to complete a session

```
POST /webhook
Content-Type: application/json
X-Signature: sha256:<hex>    # optional HMAC
{
  "event": "verification_complete",
  "session_id": "<uuid>",
  "approved": true,
  "reason": "demo pass"
}
```

This will flip the session’s result to:
```json
{
  "status": "complete",
  "outcome": "approved",
  "reason": "demo pass"
}
```

## OpenAPI

Open the spec at: `http://localhost:5000/openapi.yaml`  
You can paste the YAML into Swagger Editor (editor.swagger.io) to get a live UI.

## Test quickly with cURL

1) Create a session:
```bash
curl -s -X POST http://localhost:5000/sessions \
  -H "Content-Type: application/json" \
  -d '{"reference":"abc123","policy":{"type":"age_over","age_threshold":18}}'
```

2) Copy the `session.id` from the response, then check result:
```bash
curl -s http://localhost:5000/sessions/<SESSION_ID>/result
```

3) Complete it via webhook (no signature for demo):
```bash
curl -s -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"verification_complete","session_id":"<SESSION_ID>","approved":true,"reason":"demo pass"}'
```

4) Check result again — it should now be `complete` and `approved`.

## Postman

Import `postman/collection.json` and `postman/environment.json`, select **Yoti Sandbox (env)**, then run:
1. **Create Session** (saves SESSION_ID var)
2. **Get Result (before webhook)**
3. **Trigger Webhook (signed optional)**
4. **Get Result (after webhook)**
5. **OpenAPI YAML**

Set `WEBHOOK_SHARED_SECRET` in `.env` and in Postman env to enable signature verification.

## Public webhook (optional)

```bash
ngrok http 5000
# Use https://<ngrok-id>.ngrok.io/webhook as callback_url when creating a session
```

## Notes

- Mock only (in-memory), no persistence.
- Add real data store / auth if needed.
