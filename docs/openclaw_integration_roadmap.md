# OpenClaw Integration Roadmap

This mini roadmap covers the third major Phase 2 step: real OpenClaw integration.

It exists to turn the current prototype-safe OpenClaw flow into a truthful, documented, and explicitly safe real integration path.

## Goal

- detect real OpenClaw presence and relevant configuration state
- explain current buyer-path configuration truthfully
- stage explicit routing-configuration behavior with safety messaging
- avoid surprise local config changes during development and testing

## Why this matters

- buyer onboarding is core product behavior
- the current GUI flow is intentionally safe, but it does not yet reflect the outside world
- real integration should be explicit and reversible, not magical

## Planned slices

### Slice 1: OpenClaw discovery seam

Goal:

- add one explicit seam for discovering OpenClaw installation and current config state

Exit criteria:

- the client can distinguish not installed, installed-unconfigured, and connected states
- discovery results are visible through the client status surface

Status: completed

Summary:

- added a dedicated OpenClaw discovery seam that reads local install/config state safely
- the client can now distinguish not installed, installed-unconfigured, and configured-to-Modulo states
- the Buyer tab now reflects real discovery-backed status instead of only the prototype-safe placeholder

### Slice 2: Staged connection flow

Goal:

- add a documented plan/apply shape for OpenClaw routing configuration behavior

Exit criteria:

- the app can describe what would change before applying it
- the flow remains explicit and opt-in

Status: completed

Summary:

- added an explicit OpenClaw connection planning seam in the client layer
- separated staged review from apply so the buyer flow no longer jumps straight from discovery to configured state
- surfaced the staged plan and apply controls through the GUI while keeping the slice prototype-safe and non-mutating

### Slice 3: GUI connection experience

Goal:

- make the real OpenClaw integration flow legible in the GUI

Exit criteria:

- the GUI shows real detected state
- the GUI can present safe next steps and clear failure messaging

## Completion note

Add a short summary here when complete:

- summary: the client can now stage and explain a buyer-routing OpenClaw plan before apply, and the GUI exposes the same review/apply flow explicitly.
- proof added to repo:
  - `OpenClawConnectionPlan` and staged/apply methods in `src/modulo/client/app.py`
  - Buyer tab plan/apply state in `src/modulo/gui/controller.py` and `src/modulo/gui/window.py`
  - updated client and GUI tests covering staged review before apply
