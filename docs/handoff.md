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
- `Slice 5: Cross-machine private execution proof` is completed and now proven across separate real networks
- `Slice 6: Lightweight shared-platform advertising visibility` is completed
- the next post-proof implementation roadmap is [route_trace_visibility_roadmap.md](./route_trace_visibility_roadmap.md)
- `Slice 1: Route-trace client contract` is completed
- `Slice 2: Prototype and hosted trace fetch path` is completed
- `Slice 3: Diagnostics route-trace view` is completed
- `Slice 4: Operator trust pass` is completed
- the full route-trace visibility roadmap is now completed
- the next active implementation roadmap is [use_side_truth_roadmap.md](./use_side_truth_roadmap.md)
- `Slice 1: Use-source contract tightening` is completed
- `Slice 2: Private/shared visibility fetch truth` is completed
- `Slice 3: Use tab truth pass` is completed
- `Slice 4: Policy and empty-state trust pass` is completed
- the full use-side truth roadmap is now completed
- the next focused consumer roadmap is [continue_consumer_roadmap.md](./continue_consumer_roadmap.md)
- the next prerequisite storage roadmap is [client_local_state_roadmap.md](./client_local_state_roadmap.md)
- `Slice 1: Client state root contract` is completed
- `Slice 2: Backup and rollback metadata seam` is completed
- `Slice 1: Continue consumer registry entry` is completed
- `Slice 2: Continue config contract and file ownership` is completed
- the Modulo-owned client-local storage seam now exists for:
  - reserved root paths
  - backup target planning
  - rollback metadata planning
- real consumer writes and rollback execution still have not landed
- the current Continue consumer work is still contract-first:
  - consumer binding exists in `Mount`
  - ownership and backup boundaries are defined
  - real apply and rollback are still the next slice
- the current GUI refinement work after the completed `Use` roadmap is focused on making the second-layer `Use` flow feel calmer and more product-true without drifting toward dashboard behavior
- the `Mount` consumer registry now includes `Continue (VSCode)` under the `OpenAI API` shape so a second external consumer can be staged without changing the shape-first binding model
- the canonical product-shape guidance is now [platform_layering_spec.md](./platform_layering_spec.md)
- the current architecture discussion is [private_scope_mvp_design.md](./private_scope_mvp_design.md), which narrows the next remote-execution proof around `Local / Private / Public / Cloud`
- a future routing note is captured in [future_host_capacity_intelligence.md](./future_host_capacity_intelligence.md) for host capability profiling, warm/cold inventory truth, and dynamic idle swapping
- the private-scope design doc now explicitly captures scope governance so future `Public` support stays policy-gated and clampable back to `Private`

## What exists today

- `cloud` owns routing, job lifecycle, retry behavior, worker health, and buyer continuity leases
- `worker` owns registration, heartbeat, claiming, execution, prewarm execution path, and result reporting
- `client` owns supervision, readiness checks, session-bridge state, local discovery, host warm maintenance, and use-facing setup truth
- `gui` is a light PySide6 desktop shell split into `Use`, `Host`, and `Diagnostics`
- `session bridge` remains client-owned and separate from the worker inference bridge

The current GUI should be treated as the richer second-layer surface, not the final default product shell.
The release direction remains tray-first, with deeper truth and control exposed only by permission.

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
- the GUI now includes a `Debug` tab that surfaces the current platform URL, ready-to-run private-network worker/request commands, and an interactive network probe target
- the control plane now exposes lightweight shared-platform advertising visibility through `GET /api/platform/status`
- the platform/session visibility path now distinguishes `Private`, `Public`, and `Cloud` source truth explicitly, while preserving older network-model fields for compatibility
- the `Use` source states now distinguish active, empty, reserved, and unavailable cases with policy-aware wording instead of generic missing-data language
- the control plane now also exposes the latest routed execution through `GET /api/platform/trace/latest`
- the prototype session bridge can now read another machine's advertised model list instead of only local in-memory state
- the prototype route-trace provider can now read another machine's latest routed execution trace through the same active target flow
- the GUI `Use` tab can now reflect a remote host's advertised network models when the Debug target URL points at that host
- the client now has a dedicated `Use` contract that groups source visibility under `Local / Private / Public / Cloud` and separates visible models from route-policy truth
- the GUI can now launch with a hosted backend target preloaded, for example `https://modulo.grinningfrog.com`
- worker transport errors now surface HTTP status and edge/body details instead of collapsing to `unknown error`
- stopping hosting now explicitly unregisters the worker from the cloud registry so advertised models disappear immediately instead of lingering and timing out
- a real end-to-end request/response has now been proven across separate real networks, with desktop hosting from a home network and a laptop requester running over a cell hotspot
- the GUI shell has been tightened into a consistent pattern:
  - top-level tabs: `Use / Host / Diagnostics / Debug`
  - compact header + primary action + summary card + nested detail tabs
  - terminal-styled theme with calmer shared card styling
  - static overview copy and a split left/right footer
- the Continue consumer path now has an explicit contract layer:
  - Continue config discovery is separate from OpenClaw discovery
  - Modulo now defines a narrow managed-entry ownership contract for Continue
  - backup path and owned fields are surfaced before any real Continue file writes exist
- the client now carries a reserved local-state contract with a Modulo-owned root plus `backups`, `mounts`, `telemetry`, and manifest paths
- current Continue backup targets now resolve into Modulo-owned client state under `backups/continue_vscode`
- current Continue rollback metadata now has a reserved Modulo-owned record path under `mounts/continue_vscode.json`
- these are still planning paths only; the apply/rollback slice has not started writing real files yet
- the long-term product abstraction is now explicitly:
  - `Use`
  - `Host`
  - `Mount`
  - `Scopes`
  - `Health`

## What is still prototype-safe

- use-side model selection and routing setup
- actual OpenClaw config mutation and rollback flow
- broader trust-and-recovery polish beyond the main surfaced errors
- Windows packaging, installer, and first-run polish

Productization is intentionally deferred for now while the shared path, visibility, and policy story continue to harden.

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

- `Use` tab: model source selection shell, active route card, nested `Sources / Mount` sections
- the `Use` model picker is now an anchored nested picker panel:
  - top level: `Local / Private / Public / Cloud`
  - middle level: friendly scope labels such as `This machine` or private-scope names
  - leaf level: actual selectable models
- the `Use` picker now preserves manual branch expansion and collapse while the GUI refreshes, so the control does not fight the user while it is open
- `Mount` now starts blank by default, with no auto-selected shape or consumer
- `Mount` now behaves as a user-driven wizard:
  - choose `Shape`
  - choose a compatible `Consumer`
  - let Modulo stage the best setup it can
  - explicitly confirm before applying real edge changes
- `Mount` now filters a consumer dropdown from the selected shape, but it never auto-populates the consumer selection
- `Mount` now exposes `Continue (VSCode)` as an `OpenAI API` consumer alongside the existing OpenClaw path
- `Mount` now treats Continue as a staged contract instead of a fake-ready integration, with explicit config path, backup path, managed entry identity, and owned field list
- the redundant `Mounted Edge` card is gone, so the tab only shows the current step, relevant guidance, and consumer-specific setup when it matters
- the `Active Route` card now carries the high-level use summary directly: model, source, shape, mount, status, and one short reason
- the `Active Route` card now treats `Status` as a simple `Ready / Not ready` signal and leaves the more specific next step to the shorter `Reason` line
- `Use` selection truth now follows the actual chosen source scope, so selecting a private model surfaces `Private` instead of falling back to stale local route metadata
- `Sources` now groups `Local / Private / Public / Cloud` in one place instead of splitting them into four separate sub-tabs
- `Use` now treats `Public` as policy-reserved, `Private` as explicitly empty when no hosts are advertising, and shared scopes as read-only when the active target is unreachable
- the underlying session/platform fetch path now carries active-target and per-source visibility summaries, so `Use` truth is no longer inferred from mixed network/OpenClaw state
- `Host` tab: hosting model selection, warm-state card, execution-path truth, host toggle, worker/runtime details
- `Diagnostics` tab: smoke test summary card plus nested `Smoke / Route / Activity / Errors`
- the Diagnostics `Route` view now uses clearer operator wording for successful routes, no-route outcomes, retries, and filtered workers
- footer: left-aligned `Modulo / Hosting / Worker` key:value status with colored values, plus right-aligned transient notices

The GUI now explicitly tells the truth about whether the current worker path and latest smoke test are using `REAL` or `PROTOTYPE` execution.
The host selector only shows local installable models, and the startup path now syncs the actual hosted model to that visible local inventory instead of carrying a hidden default behind the dropdown.
The current hosted-backend path has been proven through Cloudflare Tunnel against `modulo.grinningfrog.com`, including buyer-side visibility and routed execution.

## Local workspace note

- the repo root currently contains several ACL-locked temporary directories such as `tmp*`
- `git status` may warn about permission-denied access when it scans them
- treat those folders as local workstation debris, not as project state that needs aggressive cleanup before commits
- do not attempt broad recursive deletion around them without first checking the exact resolved paths

## Next recommended starting point

Start from the completed [private_mvp_roadmap.md](./private_mvp_roadmap.md), the completed [route_trace_visibility_roadmap.md](./route_trace_visibility_roadmap.md), and the completed [use_side_truth_roadmap.md](./use_side_truth_roadmap.md) before choosing the next implementation chunk.

For the next external consumer slice, continue from [continue_consumer_roadmap.md](./continue_consumer_roadmap.md).

The most likely first useful slice is:

- a next roadmap chunk that keeps the tray-first product direction intact while refining what should surface at the `Use` layer versus `Mount` and `Scopes`
- continue the second-layer GUI cleanup around `Use` and `Mount`, especially where the current shell still feels more like a proving surface than the eventual tray-first product
- complete the next Continue consumer slices: config ownership, safe apply/rollback, and mount-surface truth
- Client local state Slices 1 and 2 are now complete, so the next concrete step before Continue Slice 3 is deciding whether telemetry breadcrumbs need to land first or whether Continue apply/rollback can proceed on the current storage seam
- Continue Slice 3 should only land after the client-local state seam exists for backups and rollback metadata
- align that `Use` work with [platform_layering_spec.md](./platform_layering_spec.md) so the current GUI keeps serving as the second-layer proving surface instead of hardening into a dashboard
- auth/policy hardening and persistence now that the shared path itself is functionally proven
- only return to packaging once the shared-network behavior feels truthful enough to lock in

If resuming in architecture mode instead of productization mode, the current non-implementation discussion is:

- [private_scope_mvp_design.md](./private_scope_mvp_design.md)

The latest architecture note in that doc is:

- keep `Public` support separate from permission to use `Public`
- treat worker scope as policy-clamped into an effective scope before routing
- allow private-network policy to forbid `Public` even if the broader platform supports it

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

Launch GUI with a shared hosted backend target preloaded:

```powershell
python -m modulo.gui_app --platform-url https://modulo.grinningfrog.com
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
- [route_trace_visibility_roadmap.md](./route_trace_visibility_roadmap.md)
- [use_side_truth_roadmap.md](./use_side_truth_roadmap.md)
- [continue_consumer_roadmap.md](./continue_consumer_roadmap.md)
- [client_local_state_roadmap.md](./client_local_state_roadmap.md)

Current architecture discussion:

- [private_scope_mvp_design.md](./private_scope_mvp_design.md)
- [private_networks_design.md](./private_networks_design.md)
- [platform_layering_spec.md](./platform_layering_spec.md)

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

- `8c733b0` `Unregister workers when hosting stops`
- `8361d54` `Surface worker transport HTTP errors`
- `e53c8d2` `Route GUI hosting through active platform target`
- `5bd081b` `Seed GUI with hosted platform target`
- `51132b0` `Document scope governance guardrails`
- `6d48088` `Refine debug target apply flow`
- `6cc4633` `Complete single machine routed proof slice`
- `42cb6b7` `Complete cross machine private proof slice`
- `9210991` `Capture future host capacity routing note`
- `9d56be0` `Add debug tab for network validation`
- `c395b1d` `Add interactive debug network probe`
- `4f36820` `Add diagnostics route trace view`
- `8fd2127` `Complete route trace trust pass`
- `cafea86` `Canonize tray-first platform layering`
- `c77626f` `Add use-side source contract`
- `c148b6f` `Add use-side visibility fetch truth`
- `3286dfc` `Reshape use tab around source groups`
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
- `f6bf222` `Align docs with hosted backend proof`
- `368854d` `Make mount setup explicit and user-driven`
- `50f2982` `Tighten active route card guidance copy`
- `d115b81` `Simplify use route readiness status`
- `fd0ef84` `Group use selector models by source`
- `f438b47` `Add nested use model picker`
- `369b781` `Replace nested model menu with anchored picker`
- `840b9b4` `Preserve use picker tree expansion state`
- `3d5d5b2` `Keep selected use branch from reopening`
- `ab4eb87` `Add Continue consumer to mount registry`
- `413f6d6` `Add Continue consumer roadmap`
- `008b38d` `Add Continue config ownership contract`

If resuming cold, start by reading:

1. [handoff.md](./handoff.md)
2. [platform_layering_spec.md](./platform_layering_spec.md)
3. [private_scope_mvp_design.md](./private_scope_mvp_design.md)
4. [private_mvp_roadmap.md](./private_mvp_roadmap.md)
