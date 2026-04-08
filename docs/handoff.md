# Handoff

This file is the quickest way to regain context when switching workstations.

## Current state

- backend phase-0 roadmap is completed
- GUI phase-0 roadmap is completed
- Phase 2 is active
- current Phase 2 step: `Step 5: Real local execution`
- current mini-roadmap status: `Slice 1` of [real_execution_roadmap.md](./real_execution_roadmap.md) is completed

## What exists today

- `cloud` owns routing, job lifecycle, retry behavior, and buyer continuity leases
- `worker` owns registration, heartbeat, claiming, execution, and result reporting
- `client` owns supervision, readiness checks, session bridge state, and local discovery
- `gui` is a light PySide6 desktop shell split into `Host`, `Buyer`, and `Diagnostics`
- `session bridge` is always client-owned and separate from the worker inference bridge

## What is real vs prototype-safe

Real today:

- local Ollama discovery
- hosting readiness preflight
- session-bridge-backed platform state in the client
- OpenClaw install/config discovery

Still prototype-safe:

- buyer model selection and routing setup
- actual OpenClaw config mutation flow
- full real local execution from the GUI path
- packaging and install polish

## Latest OpenClaw truth

The OpenClaw discovery seam now reads:

- install presence
- config-path presence
- primary model
- provider
- provider base URL

It supports both:

- `model.primary`
- `agents.defaults.model.primary`

This matters because the local OpenClaw config on the main workstation stores the primary model under `agents.defaults.model.primary`.

## GUI shape

- `Host` tab: hosting model selection, hosting readiness, hosting controls, worker state
- `Buyer` tab: OpenClaw config state plus session-bridge-backed buyer/platform state
- `Diagnostics` tab: smoke test and recent activity
- anchored footer: `Modulo <status> | Hosting <status> | Worker <status>`

## Run commands

Install editable package:

```powershell
python -m pip install -e .[gui]
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Launch GUI:

```powershell
python -m modulo.gui_app
```

Run local prototype harness:

```powershell
python -m modulo.prototype
```

Run HTTP demo server:

```powershell
python -m modulo.cloud.demo_server
```

## Current roadmap pointer

Primary sequencing doc:

- [phase_2_plan.md](./phase_2_plan.md)

Active implementation doc:

- [real_execution_roadmap.md](./real_execution_roadmap.md)

Next intended slice:

- `Slice 2: End-to-end real execution proof`
- goal: prove one real request through the supervised runtime path

## Working preferences

- keep development explicit and documented
- finish one slice before starting the next
- prefer roadmap-aligned work over offhand feature canonization
- keep `host` and `buyer` concerns separate
- keep OpenClaw config buyer-related, not hosting-related
- keep the GUI light and low-noise
- commit and push after every repo change

## Recent checkpoint

Recent meaningful commits:

- `f9bb05e` `Complete OpenClaw GUI connection slice`
- `027b2fc` `Complete OpenClaw staged connection slice`
- `62b2344` `Complete client session bridge layer`
- `51cefa3` `Add OpenClaw discovery seam`

If resuming cold, start by reading:

1. [handoff.md](./handoff.md)
2. [phase_2_plan.md](./phase_2_plan.md)
3. [real_execution_roadmap.md](./real_execution_roadmap.md)
