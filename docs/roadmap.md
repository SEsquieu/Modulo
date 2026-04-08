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

- add a real execution adapter seam while preserving the worker runtime and client supervision contracts

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

## Upcoming slices

These are ordered to keep the path coherent and consistent.

### Slice 4: Real execution adapter seam

Goal:

- keep the same worker runtime but support both a deterministic stub executor and a real Ollama-backed executor

Why this slice matters:

- it preserves fast demoability while moving execution closer to production behavior
- it keeps execution complexity inside `worker`, where it belongs

Exit criteria:

- worker runtime can be configured with `StubExecutor` or `OllamaExecutor`
- failure and success states still surface through the same shared status contract
- the demo can run without rewriting client behavior

### Slice 5: Local prototype orchestration

Goal:

- add one clear local prototype entry path that starts cloud, supervises a worker, and proves a buyer request round trip

Why this slice matters:

- it creates a repeatable proof path for development
- it gives every future slice a concrete demo to preserve

Exit criteria:

- one command or demo harness can bring up the local prototype path
- one request can traverse `client -> worker -> cloud -> worker -> response`
- operator-visible status is available during the run

### Slice 6: Client onboarding and smoke-test surface

Goal:

- give the client a minimal but truthful onboarding-facing layer for connection state, hosting state, and smoke-test results

Why this slice matters:

- it starts shaping the real product surface without turning the client into a second runtime
- it keeps the demo aligned with the eventual one-click story

Exit criteria:

- client can report connected state, hosting state, and last worker error
- client can trigger a smoke-test-oriented request path
- no routing logic is duplicated in `client`

### Slice 7: Reliability backbone

Goal:

- add the minimum timeout, retry, and unhealthy-worker behavior needed for the prototype to fail honestly

Why this slice matters:

- it prevents the prototype from only working in the happy path
- it prepares the router for continuity-aware behavior later

Exit criteria:

- claim/execute/report failures leave visible state
- unhealthy workers stop receiving work
- timeout and retry rules are tested at the control-plane level

### Slice 8: Buyer continuity leases

Goal:

- add short-lived buyer-to-worker continuity behavior inside the router to reduce cold-start thrash

Why this slice matters:

- it improves prototype UX in a way that aligns directly with the product goal
- it remains a router concern instead of leaking into client or worker shortcuts

Exit criteria:

- router can prefer a recently warm worker for an active buyer session
- leases break cleanly on timeout, health change, overload, or expiry
- continuity improves UX without obscuring routing failures

## Roadmap guardrails

Use these checks before starting a new slice:

1. Does this slice strengthen the core end-to-end proof path?
2. Does it keep `client` supervisory and `worker` execution-focused?
3. Does it preserve `cloud` as the owner of routing and coordination?
4. Can it be proven with a short, concrete exit criterion?
5. Would skipping it make the next roadmap slice harder or messier?

If the answer to most of these is no, it probably should not be the next slice.
