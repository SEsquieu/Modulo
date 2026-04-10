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

Status: not started

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

Status: not started

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

Status: not started

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

Status: not started

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
- proof added to repo:
