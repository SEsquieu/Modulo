# Real Execution Roadmap

This mini roadmap covers the fourth major Phase 2 step: real local execution.

It exists to make the current supervised prototype path exercise real Ollama-backed execution under truthful local readiness and onboarding conditions.

## Goal

- run real Ollama-backed execution through the worker path
- preserve the current `client -> worker -> cloud -> worker -> response` boundary
- make GUI state reflect real execution success and failure
- keep the deterministic stub path available when helpful for development

## Why this matters

- this is the moment the platform starts behaving like a real product instead of a structured prototype
- real execution should be proven only after discovery, readiness, and buyer integration are honest

## Planned slices

### Slice 1: Real executor selection flow

Goal:

- let the local app choose the real executor path when the environment is ready

Exit criteria:

- the worker runtime can switch cleanly between stub and real execution paths
- the selection logic is based on readiness, not hidden assumptions

### Slice 2: End-to-end real execution proof

Goal:

- prove one real request through the supervised runtime path

Exit criteria:

- a real request succeeds through the end-to-end path
- failure states are surfaced through the same client and GUI surfaces

### Slice 3: GUI truthfulness for real execution

Goal:

- make the GUI clearly indicate when execution is real versus prototype-safe

Exit criteria:

- the GUI can explain the execution mode and last real execution result
- smoke tests and worker activity remain understandable

## Completion note

Add a short summary here when complete:

- summary:
- proof added to repo:
