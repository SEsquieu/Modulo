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
4. the cloud accepts use-side requests and routes them to workers

## Current implementation status

Today the strongest part of the repo is the `cloud` package. It currently contains:

- trust-based worker selection
- in-memory worker registry
- in-memory job lifecycle
- Ollama-shaped HTTP ingress for `GET /api/tags` and `POST /api/chat`
- worker protocol endpoints for register, heartbeat, claim, result, and fail
- a demo server for local end-to-end testing

The `worker` package currently contains the beginnings of the worker runtime boundary and configuration surface.

The `client` package now contains the real supervision, readiness, session-bridge, OpenClaw discovery, and local host-truth surfaces that the desktop shell is built on.

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
- treat request continuity and warm-path UX as router concerns inside `cloud`, not `client` shortcuts

The current slice order and completion summaries live in [roadmap.md](./roadmap.md).
The GUI-specific build path lives in [gui_roadmap.md](./gui_roadmap.md).
The first GUI screen/state inventory lives in [gui_state_map.md](./gui_state_map.md).

## Development sequencing

The repo is intentionally backend-first, but the PySide client shell is now far enough along that productization and future scope-aware routing can be discussed against a real interface instead of placeholder screens.

Near-term sequence:

1. keep the `cloud` and `worker` seams truthful and scope-ready
2. sharpen shared-path truth and visibility now that private-scope remote execution has been proven through the real router and worker chain
3. preserve enough structured route-trace data for future private-network ops visibility
4. harden scope, policy, and session behavior before returning to Windows productization
5. keep future private-network work architecture-led instead of bolted onto the public path later

Scope guardrail:

- future `Public` support should be policy-gated, not self-declared by hosts
- private-network or org policy must be able to clamp a host's effective scope back down to `Private`
- the router should operate on effective scope after policy enforcement, not raw host intent

As routing evolves, prefer continuity-preserving behavior such as short-lived request leases on healthy workers when that reduces cold-start thrash without hiding failures.

Future routing note:

- [future_host_capacity_intelligence.md](./future_host_capacity_intelligence.md) captures a later design for client-built host capability profiles, warm/cold inventory truth, and dynamic idle swapping between installed models.
