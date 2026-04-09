# Handoff

This file is the quickest way to regain context when switching workstations.

## Current state

- backend phase-0 roadmap is completed
- GUI phase-0 roadmap is completed
- Phase 2 integration work is completed through `Step 5: Real local execution`
- a host-side warm-state refinement roadmap is now active before packaging
- current warm-state roadmap progress: `Slice 1`, `Slice 2`, and `Slice 3` completed
- the active next step is [productization_checklist.md](./productization_checklist.md)

## What exists today

- `cloud` owns routing, job lifecycle, retry behavior, worker health, and buyer continuity leases
- `worker` owns registration, heartbeat, claiming, execution, and result reporting
- `client` owns supervision, readiness checks, session-bridge state, local discovery, and buyer-facing setup truth
- `gui` is a light PySide6 desktop shell split into `Host`, `Buyer`, and `Diagnostics`
- `session bridge` remains client-owned and separate from the worker inference bridge

## What is real today

- local Ollama discovery
- hosting readiness preflight
- host-side model selection from installed local Ollama models, not only curated catalog entries
- session-bridge-backed platform state in the client
- OpenClaw install/config discovery
- real local execution through the supervised smoke-test path when runtime readiness passes
- GUI truth for execution mode, including `REAL` versus `PROTOTYPE`
- host-side selection of installed local Ollama models outside the curated catalog
- client-side warm-state detection for whether the selected host model is currently loaded in Ollama memory
- Host tab visibility for warm versus cold selected-model state and compact loaded-model details
- host-side prewarm lifecycle that can warm the selected model when hosting starts and surface `warming`, `warm`, and `warm_failed`
- host-side warm maintenance that refreshes the selected model when hosting stays enabled and local warmth drops away
- GUI host actions and smoke tests now run asynchronously so long local Ollama calls do not freeze the client shell

## What is still prototype-safe

- buyer model selection and routing setup
- actual OpenClaw config mutation and rollback flow
- packaging, installer, and first-run polish
- broader trust-and-recovery polish beyond the main surfaced errors

## Latest OpenClaw truth

The OpenClaw discovery seam currently reads:

- install presence
- config-path presence
- primary model
- provider
- provider base URL

It supports both:

- `model.primary`
- `agents.defaults.model.primary`

That matters because the main workstation stores the primary model under `agents.defaults.model.primary`.

## Latest GUI truth

- `Host` tab: hosting model selection, readiness, execution-path truth, hosting controls, worker state
- `Buyer` tab: OpenClaw config truth plus session-bridge-backed buyer/platform state
- `Diagnostics` tab: smoke test, execution result truth, recent activity, and continuity hints
- footer: `Modulo <status> | Hosting <status> | Worker <status>`

The GUI now explicitly tells the truth about whether the current worker path and latest smoke test are using `REAL` or `PROTOTYPE` execution.
The host selector can now choose installed local Ollama models outside the curated catalog when they are present locally.

## Next recommended starting point

Start with `Checkpoint 1: Windows packaging path` in [productization_checklist.md](./productization_checklist.md).

The most likely first useful slice is:

- prove the PySide client launches cleanly from a packaged Windows build
- capture packaging commands and any startup/resource caveats in the repo
- keep productization grounded in the now-stabilized Host, Buyer, and Diagnostics shell

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

- [productization_checklist.md](./productization_checklist.md)

## Working preferences

- keep development explicit and documented
- finish one slice before starting the next
- update the relevant roadmap or checklist when a slice is complete
- keep `host` and `buyer` concerns separate
- keep OpenClaw config buyer-related, not hosting-related
- keep the GUI light and low-noise
- commit and push after every repo change

## Recent checkpoint

Recent meaningful commits:

- `b25a33e` `Complete GUI real execution truth slice`
- `092b6c2` `Complete real execution proof slice`
- `5157a60` `Complete real executor selection slice`
- `f9bb05e` `Complete OpenClaw GUI connection slice`
- `027b2fc` `Complete OpenClaw staged connection slice`

If resuming cold, start by reading:

1. [handoff.md](./handoff.md)
2. [phase_2_plan.md](./phase_2_plan.md)
3. [productization_checklist.md](./productization_checklist.md)
