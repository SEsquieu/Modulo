# Handoff

This file is the quickest way to regain context when switching workstations.

## Current state

- backend phase-0 roadmap is completed
- GUI phase-0 roadmap is completed
- Phase 2 integration work is completed through `Step 5: Real local execution`
- the host-side warm-state roadmap is completed
- the active next implementation roadmap is [private_mvp_roadmap.md](./private_mvp_roadmap.md)
- `Slice 1: Private-scope routing contracts` is completed
- `Slice 2: Structured route-trace spine` is completed
- `Slice 3: Network-addressable worker configuration` is completed
- `Slice 4: Single-machine routed private proof` is completed
- `Slice 5: Cross-machine private execution proof` is completed in repo shape and ready for live network validation
- the current architecture discussion is [private_scope_mvp_design.md](./private_scope_mvp_design.md), which narrows the next remote-execution proof around `Local / Private / Public / Cloud`
- a future routing note is captured in [future_host_capacity_intelligence.md](./future_host_capacity_intelligence.md) for host capability profiling, warm/cold inventory truth, and dynamic idle swapping

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
- the cloud path now records structured route traces for each routing attempt, including retry attempts and filtered-worker reasons
- the worker bridge can now target a real `modulo_url` over HTTP instead of only an in-process app seam
- localhost integration coverage now proves worker register, heartbeat, claim, and report flows against the real HTTP server contract
- the local prototype harness now sends requests through the real `/api/chat` ingress while the hosted worker bridge claims and executes over the worker HTTP contract
- the single-machine private proof now captures a truthful private-scope route trace through the same path used by smoke-test and diagnostics surfaces
- the repo now includes explicit cross-machine entrypoints for a primary control-plane server and a remote worker bridge runner
- a localhost test now proves the same control-plane server plus remote-worker shape that will be used for the real network validation
- the GUI now includes a `Debug` tab that surfaces the current platform URL and ready-to-run private-network worker/request commands
- the GUI shell has been tightened into a consistent pattern:
  - top-level tabs: `Use / Host / Diagnostics / Debug`
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

Start with the live network validation run using the commands in [README.md](../README.md) and the completed [private_mvp_roadmap.md](./private_mvp_roadmap.md).

The most likely first useful slice is:

- run the primary control-plane server on one machine and the worker bridge on a second machine
- confirm one real request completes against the remote worker under a shared private-network identity
- capture the route trace and then decide whether packaging or trace-visibility work should come next

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

Run private-network control plane:

```powershell
python -m modulo.cloud.server --host 0.0.0.0 --port 8000
```

Run remote worker bridge:

```powershell
python -m modulo.worker.bridge_runner --modulo-url http://PRIMARY_MACHINE_IP:8000 --worker-id worker-laptop --model gemma4:e2b --scope private --private-network-id office-private
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

- `6cc4633` `Complete single machine routed proof slice`
- `3e64fa1` `Complete network addressable worker slice`
- `4a31eaa` `Complete route trace spine slice`
- `edd70a8` `Complete private scope routing contracts slice`
- `ddd3cec` `Clarify private scope roadmap terminology`
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
