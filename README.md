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

- [docs/roadmap.md](./docs/roadmap.md)
- [docs/gui_roadmap.md](./docs/gui_roadmap.md)
- [docs/gui_state_map.md](./docs/gui_state_map.md)
- [docs/phase_2_plan.md](./docs/phase_2_plan.md)
- [docs/session_bridge_roadmap.md](./docs/session_bridge_roadmap.md)
- [docs/host_warm_state_roadmap.md](./docs/host_warm_state_roadmap.md)
- [docs/private_scope_mvp_design.md](./docs/private_scope_mvp_design.md)
- [docs/private_mvp_roadmap.md](./docs/private_mvp_roadmap.md)
- [docs/continue_consumer_roadmap.md](./docs/continue_consumer_roadmap.md)

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
It now routes the buyer request through the real local `/api/chat` HTTP ingress while the hosted worker bridge claims and completes the job over the worker HTTP contract.

## Running the private-network proof

Primary machine:

```powershell
python -m pip install -e .
python -m modulo.cloud.server --host 0.0.0.0 --port 8000
```

Worker machine:

```powershell
python -m pip install -e .
python -m modulo.worker.bridge_runner --modulo-url http://PRIMARY_MACHINE_IP:8000 --worker-id worker-laptop --model gemma4:e2b --scope private --private-network-id office-private
```

You can also use `--stub-response "hello from remote worker"` on the worker runner if you want to validate transport and routing before relying on a real local Ollama runtime on the second machine.

## Running the GUI shell

```powershell
python -m pip install -e .[gui]
python -m modulo.gui_app
```

To launch the GUI already pointed at a shared hosted backend target:

```powershell
python -m modulo.gui_app --platform-url https://modulo.grinningfrog.com
```

You can also set `MODULO_PLATFORM_URL=https://modulo.grinningfrog.com` before launch if you want that target preloaded by default.

This launches the barebones PySide6 desktop shell against the current live client/prototype state.

The GUI currently includes:

- a `Use / Host / Diagnostics` shell with consistent nested-tab navigation, plus a deeper `Debug` surface
- a `Debug` tab with current platform URL plus ready-to-run worker and request commands for private-network validation
- an interactive `Debug` probe surface that can target another workstation's platform URL and run a real `/api/chat` network test
- lightweight shared-platform advertising visibility, so the `Use` tab can reflect another workstation's advertised network models when the Debug target points at that host
- a `Use` tab with:
  - an active route summary card
  - a `Sources` section for `Local / Private / Public / Cloud`
  - a `Mount` section that now behaves like a shape-first, consumer-second wizard
  - an anchored nested model picker grouped by source and scope
  - `Continue (VSCode)` as a real mounted consumer under the `OpenAI API` shape
- a `Host` tab with local-only model selection, warm-state card, host toggle, and worker/runtime detail tabs
- a `Diagnostics` tab with smoke-test summary, route-trace, activity, and error views
- explicit execution-path truth in host and diagnostics views so `REAL` and `PROTOTYPE` runs are clearly labeled
- async host actions and smoke tests so long Ollama calls do not freeze the UI
- a split footer with left-side shell status and right-side transient notices
- an OpenAI-compatible consumer edge for mounted clients, including `GET /v1/models` and `POST /v1/chat/completions`

Current next functional proof:

- [docs/private_scope_mvp_design.md](./docs/private_scope_mvp_design.md) narrows the source/scope model so the next remote-execution work does not harden a singular `network` pool
- [docs/private_mvp_roadmap.md](./docs/private_mvp_roadmap.md) defines the first bounded private-scope remote-execution MVP proof before packaging work resumes
- [docs/route_trace_visibility_roadmap.md](./docs/route_trace_visibility_roadmap.md) defines the next post-proof slice so routed execution becomes explainable before packaging resumes
- [docs/use_side_truth_roadmap.md](./docs/use_side_truth_roadmap.md) defines the next `Use`-side truth pass so model source visibility is clear before packaging resumes
- [docs/continue_consumer_roadmap.md](./docs/continue_consumer_roadmap.md) now tracks the first non-OpenClaw external consumer path through `Mount -> OpenAI API -> Continue (VSCode)`
- [docs/client_local_state_roadmap.md](./docs/client_local_state_roadmap.md) now tracks the prerequisite Modulo-owned client storage seam for backups, rollback metadata, and lightweight local telemetry before consumer apply/rollback work lands
- [docs/platform_layering_spec.md](./docs/platform_layering_spec.md) captures the canonical tray-first layering model so the current GUI does not drift into a dashboard-shaped product

Recent milestone:

- an end-to-end request/response has now been proven across separate real networks, with desktop hosting from a home network and a laptop requester running over a cell hotspot
- this moves Modulo beyond local-only proof into real distributed validation
- current next work should focus on truth, visibility, and policy around the shared path rather than packaging
- the newest tracked emphasis after route-trace visibility is the `Use` side: making `Local / Private / Public / Cloud` visibility honest and easy to trust
- the newest untracked GUI refinement work is making the second-layer `Use` and `Mount` flow feel calmer and more tray-first without losing truth
- the `Mount` consumer list now includes `Continue (VSCode)` under the `OpenAI API` shape so a second external consumer can be staged without disturbing the existing OpenClaw path
- the Continue path now also has an explicit config and file-ownership contract, real apply/rollback flow, and an OpenAI-compatible shim with buffered streaming compatibility so Continue can complete real prompts through Modulo
- the guiding product rule is now explicit: the current GUI is the deeper proving surface, while the release product should stay shallow, tray-first, and Hamachi-simple

## Current platform surface

The current scaffold includes these worker-facing HTTP routes:

- `POST /worker/register`
- `POST /worker/unregister`
- `POST /worker/heartbeat`
- `POST /worker/jobs/claim`
- `POST /worker/jobs/{job_id}/result`
- `POST /worker/jobs/{job_id}/fail`

They currently use simple JSON payloads and map directly onto the in-memory control plane.

The worker bridge now has both an in-process HTTP-shaped transport for local harness work and a real URL-backed transport for localhost or private-environment control-plane testing against `modulo_url`.

The current HTTP ingress also exposes:

- `GET /api/tags`
- `GET /api/platform/status`
- `POST /api/chat`
- `GET /v1/models`
- `POST /v1/chat/completions`

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

Recent functional proof highlights:

- the GUI can target a hosted backend like `https://modulo.grinningfrog.com` from launch
- the hosted path has been proven end to end through Cloudflare Tunnel for private-scope visibility and routed execution
- the same private-scope request/response path has now been exercised across separate real networks
- worker transport failures now surface HTTP status and edge/body detail instead of collapsing to `unknown error`
- stopping hosting now explicitly unregisters the worker so stale advertised models drop out of platform visibility immediately

The client and worker packages are intentionally light right now. They exist to keep the repository shaped correctly for the eventual tray app UX and local bridge architecture while the routing/control-plane core is being proven first.

## Running tests

```powershell
python -m unittest discover -s tests
```
