# GUI State Map

This document maps the current client-facing Python surface to the first physical GUI screens and interactions.

It is the implementation bridge between the backend/prototype roadmap and the GUI roadmap.

The purpose is simple:

- start the GUI from real state that already exists
- keep the GUI thin and supervisory
- identify the smallest missing view-model and event seams before any shell/bootstrap work begins

## Current source surface

The current GUI-relevant Python surface lives primarily in [app.py](../src/modulo/client/app.py).

Important current types:

- `ClientStatus`
- `OnboardingStatus`
- `SmokeTestResult`
- `WorkerStatusSnapshot`
- `WorkerBridgeConfig`

Important current client actions:

- `configure_openclaw()`
- `start_hosting()`
- `stop_hosting()`
- `restart_hosting()`
- `run_smoke_test()`
- `get_status()`
- `get_onboarding_status()`

## First GUI screens

The first physical GUI should stay extremely small.

### 1. Host tab

Purpose:

- let the user manage hosting setup and inspect the local worker

Should display:

- hosting enabled or not
- worker healthy or unhealthy
- worker details and host-side health
- hosting model setup and readiness

Primary actions:

- `Enable hosting`
- `Disable hosting`
- `Restart hosting`

Backed by:

- `OnboardingStatus`
- `ClientStatus`

### 2. Buyer tab

Purpose:

- keep buyer routing setup separate from hosting

Should display:

- OpenClaw routing configuration status
- buyer-side setup guidance
- future buyer model selection status

Primary actions:

- `Configure OpenClaw`

Backed by:

- `ClientStatus`

### 3. Diagnostics tab

Purpose:

- give the user a truthful local confidence check without exposing raw backend internals

Should display:

- smoke test pass/fail
- model used
- test prompt text
- returned response text
- error text if failed

Primary actions:

- `Run smoke test`

Backed by:

- `SmokeTestResult`
- `OnboardingStatus`

## First GUI view-model map

The GUI should not bind directly to arbitrary internals. The first shell should treat the following as the stable display shape.

### App shell view model

Derived from:

- `OnboardingStatus`

Fields the GUI needs:

- `connected_to_modulo`
- `openclaw_configured`
- `hosting_enabled`
- `worker_registered`
- `worker_healthy`
- `last_worker_error`
- `smoke_test_ok`
- `smoke_test_error`

### Worker card view model

Derived from:

- `ClientStatus.worker`

Fields the GUI needs:

- `worker_id`
- `runtime_state`
- `registered_with_cloud`
- `healthy`
- `enabled_models`
- `current_load`
- `completed_jobs`
- `failed_jobs`
- `last_error`

### Smoke-test view model

Derived from:

- `ClientStatus.smoke_test`

Fields the GUI needs:

- `ok`
- `model_id`
- `user_message`
- `response_text`
- `error`

## First GUI event map

The GUI should only need a small command surface at the start.

### Commands already supported

- configure OpenClaw routing
- start hosting
- stop hosting
- restart hosting
- run smoke test

### Commands not yet product-ready

These are conceptually part of the GUI roadmap, but should not be treated as already implemented:

- sign in / sign out
- choose network model from a real model catalog
- configure worker model selection through the GUI
- configure a real OpenClaw installation to route through Modulo
- show recent jobs/activity feed

## Missing seams before GUI bootstrap

The GUI can begin with the current client surface, but these gaps should be expected:

### 1. Polling or subscription boundary

Current state:

- GUI can call `get_status()` and `get_onboarding_status()`

Likely need:

- a simple timer-based polling loop in the first GUI shell

Deferred until later:

- push/subscription/event stream behavior

### 2. GUI-specific command adapter

Current state:

- the client supervisor methods are already small and explicit

Likely need:

- a thin adapter layer that maps GUI button clicks to supervisor calls

This should stay thin enough that it can be replaced later without changing the underlying client behavior.

### 3. View-model normalization

Current state:

- raw dataclasses are close to GUI-ready

Likely need:

- one small layer that translates Python dataclasses into the chosen GUI framework's state/store model

The GUI should not mutate domain objects directly.

## Stack implications

This state map suggests the first GUI stack should make these easy:

- calling Python directly
- polling current state on a timer
- rendering a small number of cards/panels
- packaging into a local desktop app

That means the initial stack decision should optimize for desktop pragmatism, not for a broad web-app ecosystem by default.

## Stack decision

The GUI stack for Modulo is now explicitly:

- `PySide6` for the desktop shell
- a thin Python controller layer over the existing client surface
- packaging later through the Windows desktop app path rather than through a separate web runtime

This decision matches the current architecture because:

- the client surface is already Python-native
- the GUI can call the current supervision/onboarding surface directly
- no extra JS, Rust, or browser runtime is needed to make the first physical app real

## Slice 1 completion note

`GUI Slice 1` is complete when:

- the first screens are named
- the real state backing each screen is explicit
- the first command/event surface is explicit
- the missing seams for shell/bootstrap work are identified

This document is that completion artifact.
