# Roadmap

This document is the working reference for where Modulo is in the development cycle.

It exists to keep implementation coherent, roadmap-first, and resistant to drift between `client`, `worker`, and `cloud`.

## How to use this doc

- use the current slice to decide what we build next
- add a short summary under a slice when it is completed
- keep future slices narrow and roadmap-aligned
- do not promote offhand ideas into committed roadmap work unless they clearly strengthen the core proof path

## Current phase

Current phase: `Phase 1` moving toward a working local prototype of the real `client -> worker -> cloud -> worker -> response` path.

Current active slice:

- keep extending the prototype only through roadmap-aligned slices that preserve the client-worker-cloud boundaries

Definition of progress for this phase:

- `client` supervises `worker` through shared contracts
- `worker` can register, heartbeat, claim, execute, and report
- `cloud` remains the routing and job-control authority
- the prototype path can be extended without re-dividing responsibilities

## Completed slices

### Slice 0: Repository and architecture scaffold

Status: completed

Summary:

- established the product-shaped repo split across `common`, `cloud`, `worker`, and `client`
- codified v1 policy around curated exact-match models and explicit execution modes
- documented architecture and slice-discipline rules so implementation order stays roadmap-first

Proof added to repo:

- shared contracts and v1 policy defaults
- cloud router, registry, jobs, and demo HTTP transport
- architecture and design documentation aligned with the intended UX

### Slice 1: Minimal real cloud routing core

Status: completed

Summary:

- built the in-memory cloud control plane that can route requests, track workers, and manage job state
- exposed Ollama-shaped `GET /api/tags` and `POST /api/chat`
- exposed worker control endpoints for register, heartbeat, claim, result, and fail

Proof added to repo:

- trust-weighted routing over curated exact-match models
- in-memory worker registry and job lifecycle
- test coverage for router and HTTP transport behavior

### Slice 2: Shared client-worker supervision seam

Status: completed

Summary:

- moved worker supervision concepts into shared contracts so `client` and `worker` evolve against one status/config model
- added a runnable worker bridge runtime with start, stop, heartbeat, claim, execute, and report behavior
- added a thin client supervisor that controls hosting without duplicating runtime logic

Proof added to repo:

- shared `WorkerBridgeConfig`, `WorkerStatusSnapshot`, and supervisor commands
- `WorkerBridgeRuntime` with pluggable executor and control-plane seams
- client/worker integration tests that verify successful and failed job cycles

### Slice 3: Real worker transport seam

Status: completed

Summary:

- replaced direct in-memory control-plane coupling in the worker runtime with a transport seam
- added an in-process HTTP-shaped worker transport that uses the worker protocol endpoints
- kept the client supervision surface unchanged while making the bridge exercise the real control contract

Proof added to repo:

- `InProcessWorkerHTTPTransport` for register, heartbeat, claim, result, and fail
- `WorkerBridgeRuntime` now depends on transport behavior instead of direct service access
- integration tests now run the bridge through `ModuloHTTPApp` worker endpoints

### Slice 4: Real execution adapter seam

Status: completed

Summary:

- added a real Ollama-backed executor alongside the deterministic stub executor
- carried chat messages through the cloud-to-worker claim path so real execution receives actual request content
- kept the worker runtime and client supervision contracts stable while making execution backends swappable

Proof added to repo:

- `StubExecutor` and `OllamaExecutor` in the worker package
- `ChatRequest` and worker claim transport now preserve message payloads
- executor tests verify payload construction and error handling for the Ollama path

### Slice 5: Local prototype orchestration

Status: completed

Summary:

- added one local prototype harness that wires cloud, client supervision, worker transport, and worker execution into a repeatable demo path
- kept the orchestration in-process so the prototype remains fast to run while still respecting the package boundaries
- made the prototype runnable from a single module entry point

Proof added to repo:

- `LocalPrototypeHarness` and `python -m modulo.prototype`
- prototype tests for boot and buyer round trip
- repo docs now show how to run the local prototype path

### Slice 6: Client onboarding and smoke-test surface

Status: completed

Summary:

- extended the client-facing surface with onboarding status reporting for connection, hosting, worker health, and worker registration
- added a smoke-test result model and a client smoke-test path that reuses the existing prototype harness
- kept the client supervisory by delegating the actual smoke-test round trip to the harness instead of duplicating runtime logic

Proof added to repo:

- `OnboardingStatus` and `SmokeTestResult` on the client side
- client smoke-test support wired through the local prototype harness
- tests covering both onboarding state and smoke-test reporting

### Slice 7: Reliability backbone

Status: completed

Summary:

- added minimal retry-on-failure behavior in the control plane so a failed claimed job can be reassigned once to another eligible worker
- added timeout handling and unhealthy-worker marking so failed workers stop receiving work
- made client/prototype reporting reflect unhealthy worker state during failed smoke tests

Proof added to repo:

- cloud retry and timeout handling in the in-memory service and job queue
- router tests covering retry-on-failure and timeout behavior
- prototype/client tests covering unhealthy-worker reporting after execution failure

### Slice 8: Buyer continuity leases

Status: completed

Summary:

- added short-lived buyer-to-worker continuity leases inside the cloud service so repeat requests can prefer a recently warm worker
- made leases soft by expiring them after inactivity and breaking them when workers become unhealthy or are rehomed
- kept continuity fully inside the routing/control-plane path instead of pushing that logic into the client or worker

Proof added to repo:

- buyer identity on chat requests plus an in-memory lease manager in the cloud layer
- lease-aware routing that prefers an eligible leased worker before falling back to trust-weighted selection
- tests covering buyer continuity, lease expiry, and lease break/rehome behavior

## Upcoming slices

The next committed implementation path is:

- [private_mvp_roadmap.md](./private_mvp_roadmap.md)

Current active slice:

- `Slice 1: Private-scope routing contracts`

Why it is next:

- the true MVP proof is routed execution to a non-local worker inside a bounded private scope
- the router should become scope-aware before the old singular `network` assumption hardens further
- structured route traces should begin with the next remote-execution slices so future private-network ops visibility does not require a large retrofit

## Roadmap guardrails

Use these checks before starting a new slice:

1. Does this slice strengthen the core end-to-end proof path?
2. Does it keep `client` supervisory and `worker` execution-focused?
3. Does it preserve `cloud` as the owner of routing and coordination?
4. Can it be proven with a short, concrete exit criterion?
5. Would skipping it make the next roadmap slice harder or messier?

If the answer to most of these is no, it probably should not be the next slice.
