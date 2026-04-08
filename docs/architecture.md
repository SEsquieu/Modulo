# Architecture

## Product shape

Modulo is being organized around three product-facing runtime boundaries plus shared contracts:

- `client`: the local tray-first user application
- `worker`: the local background bridge that talks to Ollama and the cloud
- `cloud`: the hosted routing and job control plane
- `common`: the shared contracts and policy surface used across all three

This structure is intentional. It keeps the repository aligned with the eventual user experience:

1. the user installs the client
2. the client performs onboarding and configuration
3. the client can enable or supervise the worker bridge locally
4. the cloud accepts buyer requests and routes them to workers

## Current implementation status

Today the strongest part of the repo is the `cloud` package. It currently contains:

- trust-based worker selection
- in-memory worker registry
- in-memory job lifecycle
- Ollama-shaped HTTP ingress for `GET /api/tags` and `POST /api/chat`
- worker protocol endpoints for register, heartbeat, claim, result, and fail
- a demo server for local end-to-end testing

The `worker` package currently contains the beginnings of the worker runtime boundary and configuration surface.

The `client` package currently contains only lightweight placeholders to keep the repo shaped correctly for the future tray app and onboarding UX.

## Boundary rules

These rules should guide future development:

- `common` should hold contracts and policy types, not product-specific orchestration.
- `cloud` owns routing, trust scoring, worker/job coordination, and public API behavior.
- `worker` owns local execution, heartbeats, job claiming, and Ollama integration.
- `client` owns onboarding, user-visible state, tray interactions, and local configuration.
- `client` should not contain routing logic.
- `worker` should report facts; `cloud` should make routing decisions.

## Slice discipline

These rules should guide implementation order:

- prioritize slices that move the end-to-end demo closer to real proof
- keep `client` and `worker` aligned through shared contracts rather than duplicated behavior
- avoid widening the surface area unless the new behavior clearly supports the roadmap
- treat buyer continuity and warm-path UX as router concerns inside `cloud`, not `client` shortcuts

The current slice order and completion summaries live in [roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/roadmap.md).
The GUI-specific build path lives in [gui_roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/gui_roadmap.md).

## Development sequencing

The repo is intentionally backend-heavy right now because the routing and worker protocol need to be real before the tray client can be built around them confidently.

Near-term sequence:

1. keep hardening the `cloud` and `worker` seam
2. scaffold the real worker bridge against the worker HTTP endpoints
3. expose smoke-test and onboarding-friendly APIs for the client
4. build the tray-first client on top of those stable contracts

As routing evolves, prefer continuity-preserving behavior such as short-lived buyer leases on healthy workers when that reduces cold-start thrash without hiding failures.
