# Modulo

Initial scaffold for the Modulo v1 platform.

This repo currently codifies the recommended v1 decisions from the design doc:

- curated supported model list
- exact model-name matching in v1
- separate execution modes: `local`, `network`, `cloud`
- network routing based on trust and health
- exact-model trusted cloud fallback only
- no model substitution in v1

## Repo shape

The repository is organized around the product we actually want to ship:

- `src/modulo/common`: shared contracts, catalog, and v1 policy defaults
- `src/modulo/cloud`: hosted control plane, router, job system, and Ollama-shaped HTTP transport
- `src/modulo/worker`: local worker bridge/runtime code
- `src/modulo/client`: tray-first client and onboarding-facing client code
- `tests`: contract and transport tests for the current scaffold

This keeps the codebase aligned with the intended UX:

- users install the `client`
- the `client` manages local worker behavior through the `worker` bridge
- the hosted `cloud` layer owns routing, trust, and job coordination

## Running the demo server

```powershell
python -m pip install -e .
python -m modulo.cloud.demo_server
```

Then try:

```powershell
curl http://127.0.0.1:8000/api/tags
curl -Method Post http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"model":"llama3.1:8b","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

## Current platform surface

The current scaffold includes these worker-facing HTTP routes:

- `POST /worker/register`
- `POST /worker/heartbeat`
- `POST /worker/jobs/claim`
- `POST /worker/jobs/{job_id}/result`
- `POST /worker/jobs/{job_id}/fail`

They currently use simple JSON payloads and map directly onto the in-memory control plane.

The current HTTP ingress also exposes:

- `GET /api/tags`
- `POST /api/chat`

## Current status

This repo currently proves a tight Phase 0/1 backend slice:

- trust-weighted routing over curated exact-match models
- in-memory worker registry and job lifecycle
- worker protocol endpoints for register, heartbeat, claim, complete, and fail
- Ollama-shaped `/api/chat` and `/api/tags` transport
- a seeded demo worker for local end-to-end testing

The client and worker packages are intentionally light right now. They exist to keep the repository shaped correctly for the eventual tray app UX and local bridge architecture while the routing/control-plane core is being proven first.

## Running tests

```powershell
python -m unittest discover -s tests
```
