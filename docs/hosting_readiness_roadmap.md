# Hosting Readiness Roadmap

This mini roadmap covers the second major Phase 2 step: real hosting readiness.

It exists to turn hosting setup from a config choice into a truthful preflight-backed readiness state.

## Goal

- validate that the selected model exists locally
- validate that Ollama is reachable for that model
- validate that the worker can host through the current local runtime path
- expose readiness failures in a way the GUI can explain clearly

## Why this matters

- “ready to host” should mean something operational, not just “a model was selected”
- worker health and hosting onboarding should be grounded in the same facts
- later real execution work will be cleaner if readiness failures are already explicit

## Planned slices

### Slice 1: Hosting preflight contract

Status: completed

Summary:

- added a dedicated hosting preflight contract that reports pass/fail readiness, blocking reason, and individual checks
- separated preflight failure reasons from general setup guidance and runtime execution errors
- threaded the preflight result through the existing hosting setup state so later runtime checks can plug into the same surface

Proof added to repo:

- `HostingPreflightStatus` and `HostingPreflightCheck` in the client layer
- hosting setup state now includes preflight outcome and blocking reason
- client tests covering both passing and failing preflight states

### Slice 2: Worker and runtime checks

Status: completed

Summary:

- added a replaceable local runtime probe that validates whether Ollama can resolve the selected model
- threaded the runtime probe into hosting preflight so readiness now depends on both inventory truth and runtime response
- kept the runtime probe outside the GUI and worker layers so it remains a client-facing readiness seam

Proof added to repo:

- `OllamaHostingRuntimeProbe` and `HostingRuntimeProbeStatus` in the client layer
- hosting preflight now includes a runtime-resolution check
- client tests covering both passing and failing runtime probe cases

### Slice 3: GUI readiness flow

Goal:

- surface real readiness in the hosting setup panel and hosting controls

Exit criteria:

- the GUI can show why hosting is or is not ready
- the GUI no longer relies on config-only readiness language

## Completion note

Add a short summary here when complete:

- summary:
- proof added to repo:
