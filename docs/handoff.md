# Handoff

This file is the quickest way to regain context when switching workstations.

## Current state

- backend phase-0 roadmap is completed
- GUI phase-0 roadmap is completed
- Phase 2 integration work is completed through `Step 5: Real local execution`
- the host-side warm-state roadmap is completed
- the active next implementation roadmap is [private_mvp_roadmap.md](./private_mvp_roadmap.md)
- the current architecture discussion is [private_scope_mvp_design.md](./private_scope_mvp_design.md), which narrows the next remote-execution proof around `Local / Private / Public / Cloud`

## What exists today

- `cloud` owns routing, job lifecycle, retry behavior, worker health, and buyer continuity leases
- `worker` owns registration, heartbeat, claiming, execution, prewarm execution path, and result reporting
- `client` owns supervision, readiness checks, session-bridge state, local discovery, host warm maintenance, and use-facing setup truth
- `gui` is a light PySide6 desktop shell split into `Use`, `Host`, and `Diagnostics`
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
- the GUI shell has been tightened into a consistent pattern:
  - top-level tabs: `Use / Host / Diagnostics`
  - compact header + primary action + summary card + nested detail tabs
  - terminal-styled theme with calmer shared card styling
  - static overview copy and a split left/right footer

## What is still prototype-safe

- use-side model selection and routing setup
- actual OpenClaw config mutation and rollback flow
- broader trust-and-recovery polish beyond the main surfaced errors
- Windows packaging, installer, and first-run polish

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

- `Use` tab: model source selection shell, active route card, nested `Route / Local / Network / Cloud` sections, OpenClaw route truth
- `Host` tab: hosting model selection, warm-state card, execution-path truth, host toggle, worker/runtime details
- `Diagnostics` tab: smoke test summary card plus nested `Smoke / Activity / Errors`
- footer: left-aligned `Modulo / Hosting / Worker` key:value status with colored values, plus right-aligned transient notices

The GUI now explicitly tells the truth about whether the current worker path and latest smoke test are using `REAL` or `PROTOTYPE` execution.
The host selector only shows local installable models, and the startup path now syncs the actual hosted model to that visible local inventory instead of carrying a hidden default behind the dropdown.

## Next recommended starting point

Start with `Slice 1: Private-scope routing contracts` in [private_mvp_roadmap.md](./private_mvp_roadmap.md).

The most likely first useful slice is:

- introduce the minimum request and worker scope contracts needed for `private` remote execution
- keep the old singular `network` assumption from hardening any further
- make route traces structured enough that future private-network ops visibility will not require a large retrofit

If resuming in architecture mode instead of productization mode, the current non-implementation discussion is:

- [private_scope_mvp_design.md](./private_scope_mvp_design.md)

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

- [private_mvp_roadmap.md](./private_mvp_roadmap.md)

Current architecture discussion:

- [private_scope_mvp_design.md](./private_scope_mvp_design.md)

## Working preferences

- keep development explicit and documented
- finish one slice before starting the next
- update the relevant roadmap or checklist when a slice is complete
- keep `host` and `use` concerns separate
- keep OpenClaw config buyer-related, not hosting-related
- keep the GUI light and low-noise
- commit and push after every repo change

## Recent checkpoint

Recent meaningful commits:

- `71cb7fc` `Refresh docs and workstation handoff context`
- `da37572` `Refine private networks source and scope model`
- `755d0ca` `Add private networks architecture note`
- `a8efbf2` `Stabilize overview copy and split footer status`
- `bc6865a` `Reshape diagnostics tab to match shell layout`
- `9134ddf` `Increase host toggle button text size`
- `2cbc0f8` `Blend host toggle into terminal theme`
- `a9e5563` `Refine info card styling for sleek terminal UI`
- `14bd1b6` `Sync initial host model to local inventory`

If resuming cold, start by reading:

1. [handoff.md](./handoff.md)
2. [private_scope_mvp_design.md](./private_scope_mvp_design.md)
3. [private_mvp_roadmap.md](./private_mvp_roadmap.md)
