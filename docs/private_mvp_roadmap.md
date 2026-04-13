# Private MVP Roadmap

This mini roadmap covers the next functional proof after the current local execution and host warm-state work.

It exists to prove that Modulo can route a real request to a model hosted through the worker bridge on another machine inside a bounded private scope, while staying compatible with the future `Local / Private / Public / Cloud` source model.

## Goal

- prove one real non-local execution path through the router
- treat bounded private remote execution as the first `Private`-style execution proof
- keep the existing `client -> cloud -> worker -> Ollama` responsibilities intact
- capture structured route-trace data that can later power private-network ops visibility

## Why this matters

- this is the real MVP proof more than packaging is
- remote execution inside a private bounded scope exercises the same router and worker seams that later enterprise or broader private-network execution will use
- if scope is not narrowed now, the old singular `network` assumption will get more expensive to undo later
- route-trace observability needs to start with the router path, not as a retrofit after private networks exist

## Planned slices

### Slice 1: Private-scope routing contracts

Goal:

- introduce the minimum shared contract shape needed for the router to distinguish `private` work from generic non-local work

Exit criteria:

- request-side scope can resolve to at least `local`, `private`, or `cloud`
- worker advertisements can carry a serving scope and lightweight private-network identity
- router eligibility can filter by scope before worker ranking happens

Notes:

- this slice should stay narrow and contract-led
- old `network` vocabulary may still exist in some surfaces, but new routing assumptions should stop depending on a singular network pool

Status: completed

Summary:

- added explicit request-side scope and private-network identity to shared routing contracts without forcing a large naming refactor
- added worker-side serving scope and private-network identity to worker registration and bridge configuration
- made router eligibility filter by scope and private-network identity before trust scoring

Proof added to repo:

- shared `RouteScope` contract plus request-side and worker-side private-network identity in `src/modulo/common/contracts.py`
- scope-aware router eligibility in `src/modulo/cloud/router.py`
- scope-preserving worker registration and claim transport in `src/modulo/cloud/http.py` and `src/modulo/worker/transport.py`
- router and HTTP tests covering private-scope filtering and private-network identity matching

### Slice 2: Structured route-trace spine

Goal:

- capture structured route data for each routed request inside the cloud path

Exit criteria:

- the router/control plane emits a trace object or structured record for each request
- the trace includes scope resolution, worker eligibility, selection reason, and final outcome
- tests prove route traces for both successful selection and filtered/retry cases

Notes:

- this is the foundation for future private-network ops visibility
- machine-readable fields matter more than polished UI in this slice

Status: completed

Summary:

- added a structured in-memory route-trace record for each routing attempt in the cloud control path
- kept retries as separate trace attempts so route history stays useful for future health and ops aggregation
- preserved machine-readable worker filter reasons, selected worker facts, scope resolution, and terminal outcomes without adding any dashboard surface yet

Proof added to repo:

- `RouteTraceRecord` and `FilteredWorkerReason` in `src/modulo/common/contracts.py`
- route-trace draft generation in `src/modulo/cloud/router.py`
- trace lifecycle storage and attempt updates in `src/modulo/cloud/runtime.py`
- job trace-id threading in `src/modulo/cloud/jobs.py`
- router tests covering successful trace capture and retry-attempt trace history

### Slice 3: Network-addressable worker configuration

Goal:

- make the worker bridge and cloud/API configuration cleanly usable across a real private environment instead of only in-process assumptions

Exit criteria:

- cloud URL and worker configuration can target a real reachable API endpoint
- the worker bridge can register, heartbeat, claim, and report over that address cleanly
- one machine can still run a valid single-box proof by hitting the same HTTP/control path

Notes:

- this slice should avoid adding packaging or installer work
- the point is transport truth, not desktop polish

Status: completed

Summary:

- added a real URL-backed worker HTTP transport so the bridge can target `modulo_url` over the actual control-plane API
- preserved private-scope identity and route-trace threading across the worker claim path instead of only in in-process transport
- proved a valid single-machine localhost configuration against the real HTTP server without turning this slice into the full routed-ingress proof

Proof added to repo:

- `UrllibWorkerHTTPTransport` in `src/modulo/worker/transport.py`
- worker claim payload now includes `trace_id` in `src/modulo/cloud/http.py`
- localhost endpoint integration coverage in `tests/test_worker_transport.py`
- HTTP contract coverage updated in `tests/test_http_app.py`

### Slice 4: Single-machine routed private proof

Goal:

- prove one request that still traverses the real router and worker chain on a single machine before using a second device

Exit criteria:

- the request enters through the cloud/API path
- the router produces a route trace
- the worker claims and executes through the real worker bridge path
- the result returns successfully and is observable through the same smoke-test or diagnostics surfaces

Notes:

- this is a staging slice, not the final proof
- it is acceptable if the worker and cloud share a machine, as long as the routing chain remains truthful

Status: completed

Summary:

- moved the local prototype harness onto the real HTTP ingress so requests now enter through `/api/chat` instead of directly calling the service layer
- ran the hosted worker through the real worker-bridge HTTP path in queued mode, with the router producing a private-scope route trace and the worker completing the job asynchronously
- kept the smoke-test and diagnostics-facing client surfaces intact while making the single-machine proof much closer to the eventual cross-machine path

Proof added to repo:

- queued chat wait mode in `src/modulo/cloud/http.py`
- real single-machine routed ingress harness in `src/modulo/prototype.py`
- prototype tests covering routed round-trip, failure surfacing, and private route-trace capture in `tests/test_prototype.py`

### Slice 5: Cross-machine private execution proof

Goal:

- prove the same routed execution path with the worker on a second machine inside the same private scope

Exit criteria:

- a second machine can run the worker bridge against the primary machine's cloud/API
- the remote worker advertises a model and is eligible for routing
- one real request completes against that remote worker
- the route trace shows the worker selection and final execution outcome cleanly

Notes:

- this slice is the true private remote-execution MVP proof
- after this succeeds, packaging can resume with much more confidence

Status: completed

Summary:

- added explicit primary-machine and worker-machine entrypoints so the private proof can run as a real control-plane server plus remote worker bridge pair
- kept the worker registration, claim, execution, and route-trace path identical to the single-machine proof so cross-machine behavior stays comparable
- proved the cross-machine-style flow on localhost with separate HTTP server and worker bridge processes-in-shape before handing it off for a real network test
- the same routed request/response path has now also been proven live across separate real networks, with the host on a home network and the requester on a laptop over a cell hotspot

Proof added to repo:

- primary control-plane entrypoint in `src/modulo/cloud/server.py`
- remote worker bridge runner in `src/modulo/worker/bridge_runner.py`
- cross-machine-style private flow coverage in `tests/test_private_network_flow.py`
- operator run commands in `README.md`

### Slice 6: Lightweight shared-platform advertising visibility

Goal:

- let a buyer-side GUI point at a shared control plane and see the currently advertised network models without building full discovery or trust UX yet

Exit criteria:

- the control plane exposes a lightweight platform-visibility read endpoint
- the client session bridge can read that endpoint from another machine
- the GUI `Use` tab updates its network-model visibility from the selected debug target
- tests prove one harness can see another harness's advertised model list

Notes:

- keep this narrow and visibility-only
- do not turn this slice into full network discovery, trust ranking, or route-health UX

Status: completed

Summary:

- added a lightweight shared-platform status endpoint so buyers can read advertised network models and buyer-routing context from the active control plane
- taught the prototype session bridge to treat the Debug target URL as a real platform visibility target instead of only a probe destination
- wired the GUI so the `Use` tab now reflects the selected Debug target's advertised network models, which closes the exact cross-machine selection gap discovered during live testing

Proof added to repo:

- `GET /api/platform/status` in `src/modulo/cloud/http.py`
- remote-aware prototype session bridge in `src/modulo/prototype.py`
- Debug-target-driven visibility sync in `src/modulo/gui/controller.py`
- HTTP, prototype, and GUI coverage for remote advertising visibility in `tests/test_http_app.py`, `tests/test_prototype.py`, and `tests/test_gui_controller.py`

## Route-trace requirement

Every slice in this roadmap should preserve the future ability to expose route traces in operator surfaces.

The minimum trace story for this roadmap should preserve fields or equivalents for:

- request identity
- selected source
- resolved scope
- private network identity
- requested model
- eligible workers
- filtered worker reasons
- selected worker
- route reason
- continuity or warm-path contribution
- retry or rehome behavior
- final result or failure

This does not require a dashboard yet, but it must leave enough truthful data for one later.

## Completion note

Add a short summary here when the roadmap is complete:

- summary:
  - Modulo now proves a bounded private-scope execution path across machines, including a Cloudflare-hosted backend target, light buyer-side visibility for advertised network models, and immediate worker cleanup when a host goes offline.
- proof added to repo:
- shared control-plane and worker entrypoints, route traces, cross-machine worker transport, lightweight shared-platform advertising visibility, hosted-backend GUI targeting, improved worker transport error surfacing, and explicit worker unregister on unhost
- the same bounded private-scope routed path is now proven both in localhost process shape and in a real cross-network request/response
