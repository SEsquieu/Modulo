# GUI Roadmap

This document is the working reference for how the physical Modulo GUI client should be built.

It exists to keep GUI work explicit, phased, and aligned with the current `client -> worker -> cloud` architecture rather than letting UI work drift into a second runtime.

## How to use this doc

- use the current GUI slice to decide what UI work should happen next
- add a short summary under a slice when it is completed
- keep GUI slices thin and demonstrable
- do not move runtime logic into the GUI just because the GUI needs to visualize it
- only add new GUI slices when they clearly strengthen the installable product path

## Product intent

The GUI client should become the physical local application a user installs to manage both buyer and hosting behavior.

The GUI is responsible for:

- sign-in and connection state
- onboarding flows
- OpenClaw connection controls
- hosting controls
- worker and smoke-test visibility
- user-visible activity, health, and simple model configuration

The GUI is not responsible for:

- routing decisions
- retry or lease behavior
- worker job protocol semantics
- execution logic
- cloud control-plane policy

Those remain in `cloud` and `worker`. The GUI should supervise, visualize, and guide.

## Current GUI phase

Current GUI phase: `Phase 0` planning and thin-client surface definition.

Current active GUI slice:

- maintain and refine the GUI while the backend shifts from prototype-safe behavior toward real integrations

Definition of progress for this phase:

- GUI work is documented as a separate roadmap
- GUI slices are ordered around the installable product path
- the GUI roadmap remains consistent with the backend roadmap and architecture guardrails

## Completed GUI slices

### GUI Slice 1: Client surface inventory and state map

Status: completed

Summary:

- mapped the existing client supervision, onboarding, smoke-test, and worker-status types onto the first GUI screens
- identified the smallest first GUI screens as the home screen, worker panel, and smoke-test/diagnostics panel
- documented the first command surface and the missing seams that the shell/bootstrap slice must account for

Proof added to repo:

- [gui_state_map.md](/Users/16096/Desktop/Projects/Modulo/docs/gui_state_map.md)
- explicit mapping from current Python client state to GUI view-model concerns
- explicit event/command map for the first GUI shell

### GUI Slice 2: Barebones local shell and app bootstrap

Status: completed

Summary:

- committed the GUI stack to PySide6 for a thin cross-platform desktop shell that stays in Python
- added a small GUI controller layer so the shell reads real client state without embedding runtime logic in widgets
- stood up a minimal launchable desktop window that renders live client/worker/smoke-test state and can trigger existing client actions

Proof added to repo:

- PySide6 chosen explicitly as the GUI stack
- `python -m modulo.gui_app` launch path plus a minimal controller-backed window
- controller tests covering shell state refresh and core actions

### GUI Slice 3: Onboarding home screen

Status: completed

Summary:

- reshaped the first PySide window into a clearer onboarding-oriented home screen instead of a raw diagnostic layout
- centered the home screen on buyer/hosting readiness, worker health, and smoke-test status
- kept the screen grounded in live controller state so it stays honest as the backend evolves

Proof added to repo:

- improved PySide home-screen layout and status-card presentation
- richer controller summaries for connection, hosting, worker health, and smoke-test outcome
- controller tests that validate the home-screen state summaries

### GUI Slice 4: Hosting controls and worker panel

Status: completed

Summary:

- turned the PySide shell into a real hosting control surface with start, stop, and restart actions wired to the existing client supervisor
- expanded the worker panel to show registration, health, recent activity, last job state, and last error from the live worker status contract
- kept all worker behavior in the existing client and worker layers so the GUI remains supervisory rather than operational

Proof added to repo:

- dedicated hosting-controls section in the PySide shell
- richer worker panel backed by `WorkerStatusSnapshot` fields that already exist
- controller tests validating action enablement and worker activity summaries

### GUI Slice 5: Smoke test and diagnostics panel

Status: completed

Summary:

- turned the smoke-test area into a clearer diagnostics flow with prompt entry, explicit pass/fail labeling, and richer result details
- added a combined diagnostics summary so smoke-test output and last worker error are visible together in one place
- kept the GUI bound to the existing smoke-test runner and worker status surface rather than inventing a separate debugging path

Proof added to repo:

- prompt-driven smoke-test panel in the PySide shell
- diagnostics summary and details backed by `SmokeTestResult` and `OnboardingStatus`
- controller tests covering smoke-test prompt retention and diagnostics summaries

### GUI Slice 6: OpenClaw connection flow

Status: completed

Summary:

- added a dedicated OpenClaw panel with explicit connected or disconnected state, safe prototype messaging, and connect or disconnect controls
- extended the client and GUI state surfaces so the app can explain what the current OpenClaw path is doing instead of treating it as a silent boolean
- kept the flow honest that local OpenClaw configuration is not being edited yet while still giving the GUI a real onboarding-shaped action path

Proof added to repo:

- explicit OpenClaw configuration status surfaced through the client status
- dedicated OpenClaw section in the PySide shell with status, details, and safety note
- controller tests covering connect, disconnect, and safe prototype messaging

### GUI Slice 7: Hosting setup flow

Status: completed

Summary:

- added a dedicated hosting-setup panel with model selection, readiness summary, and explicit setup guidance
- extended the client status surface so the GUI reads selected model and setup readiness from real worker config instead of widget-only state
- kept hosting enablement explicit and opt-in while making the selected curated model visible before the worker is started

Proof added to repo:

- explicit `HostingSetupStatus` surfaced through the client status
- dedicated hosting setup section in the PySide shell with model visibility and readiness details
- client and controller tests covering setup-state synchronization and model selection

### GUI Slice 8: Activity and continuity visibility

Status: completed

Summary:

- added a user-facing activity panel that shows recent jobs and a simple continuity summary without exposing raw backend internals
- extended the prototype and client-facing state so recent job records and lease reuse hints are available to the GUI through the same thin supervision path
- kept the presentation lightweight and legible instead of turning the GUI into an operator console

Proof added to repo:

- activity visibility surfaced through the client status and prototype harness
- dedicated activity section in the PySide shell with recent job lines and continuity summary
- prototype and controller tests covering recent activity and lease reuse visibility

## Next GUI work

The planned phase-0 GUI slices are now complete.

From here, new GUI work should be added only when it clearly supports one of these goals:

- replacing prototype-safe placeholders with real integrations
- tightening installability and packaging for a physical desktop app
- refining usability based on real local testing without moving runtime logic into the GUI

## GUI guardrails

Use these checks before starting a new GUI slice:

1. Does this slice strengthen the real installable product path?
2. Does it read from real client/worker/cloud state rather than inventing fake UI state?
3. Does it keep routing and execution logic outside the GUI?
4. Can it be demonstrated in a small, real interaction?
5. Would it still make sense if the backend contracts stayed exactly as they are today?

If the answer to most of these is no, it probably should not be the next GUI slice.

## GUI stack decision rule

The first GUI stack should be chosen for:

- fast local iteration
- easy packaging into a physical desktop app
- low friction when calling the existing Python client surface
- a clear path to tray-style behavior later

Do not pick a stack primarily for visual polish. Pick the one that lets the product become real fastest without forcing a rewrite of the supervision boundary.
