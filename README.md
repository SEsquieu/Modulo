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

## Development posture

This repo should grow through tight vertical slices that strengthen the roadmap-critical demo path.

- build toward the one end-to-end proof, not side ideas in isolation
- keep `client` thin and supervisory so `worker` remains the real runtime seam
- only canonize new behavior when it clearly improves the core buyer-to-worker path
- prefer clean continuity and shared contracts over duplicate logic or package drift

Roadmap reference:

- [docs/roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/roadmap.md)
- [docs/gui_roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/gui_roadmap.md)
- [docs/gui_state_map.md](/Users/16096/Desktop/Projects/Modulo/docs/gui_state_map.md)

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

## Running the local prototype

```powershell
python -m pip install -e .
python -m modulo.prototype
```

This boots the in-process cloud control plane, starts a supervised worker through the client-facing path, and runs one buyer round trip through the local prototype harness.

The local prototype now also supports a client-facing smoke-test path through the same harness and worker/runtime seams.

## Running the GUI shell

```powershell
python -m pip install -e .[gui]
python -m modulo.gui_app
```

This launches the barebones PySide6 desktop shell against the current live client/prototype state.

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

High-value next routing behavior to add:

- short-lived buyer-to-worker continuity leases to avoid repeated cold starts
- lease break/timeout behavior driven by health, load, and execution failures

The current prototype now includes short-lived buyer continuity leases in the cloud routing path so follow-up requests can prefer a recently warm eligible worker without moving routing logic into the client or worker.

The client and worker packages are intentionally light right now. They exist to keep the repository shaped correctly for the eventual tray app UX and local bridge architecture while the routing/control-plane core is being proven first.

## Running tests

```powershell
python -m unittest discover -s tests
```
