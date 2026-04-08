# Phase 2 Plan

This document is the sequencing reference for the next development phase after the initial backend and GUI roadmaps.

The purpose of this phase is to replace prototype-safe placeholders with truthful local integrations while keeping `client`, `worker`, `cloud`, and `gui` aligned.

## How to use this doc

- complete each step in order
- do not begin the next step until the current step is completed and summarized
- use the linked mini roadmaps for implementation details
- use the productization checklist only after the integration mini roadmaps are complete

## Phase intent

Phase 2 should make Modulo feel usable and useful on a real workstation.

That means:

- local readiness is based on detected facts, not assumptions
- hosting readiness is based on executable preflight checks
- OpenClaw onboarding is explicit and truthful
- real local execution can be exercised through the same path the GUI supervises
- installability and operator trust improve only after the underlying integrations are real

## Sequence

### Step 1: Local Ollama discovery

Status: not started

Roadmap:

- [ollama_discovery_roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/ollama_discovery_roadmap.md)

Why first:

- every later hosting and execution claim should be grounded in what is actually installed locally

Completion gate:

- the client can detect Ollama availability and show curated-versus-installed model state truthfully

### Step 2: Real hosting readiness

Status: not started

Roadmap:

- [hosting_readiness_roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/hosting_readiness_roadmap.md)

Why second:

- once local discovery is real, the app can move from “configured” to “actually ready”

Completion gate:

- hosting readiness in the GUI is driven by real preflight checks instead of config alone

### Step 3: Real OpenClaw integration

Status: not started

Roadmap:

- [openclaw_integration_roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/openclaw_integration_roadmap.md)

Why third:

- buyer onboarding should become real only after the app can speak honestly about local readiness

Completion gate:

- the GUI can detect and explain the real OpenClaw state and stage a documented connection flow safely

### Step 4: Real local execution

Status: not started

Roadmap:

- [real_execution_roadmap.md](/Users/16096/Desktop/Projects/Modulo/docs/real_execution_roadmap.md)

Why fourth:

- real execution is most valuable after the app can truthfully identify local models, readiness, and buyer configuration

Completion gate:

- a real Ollama-backed execution path can be exercised end to end from the supervised client flow

### Step 5: Productization checklist

Status: not started

Checklist:

- [productization_checklist.md](/Users/16096/Desktop/Projects/Modulo/docs/productization_checklist.md)

Why checklist format instead of a full roadmap:

- packaging and trust polish are important, but they are smaller gated efforts that should follow the real integrations rather than compete with them

Completion gate:

- the Windows app path is installable enough to test like a product, and the main reliability or trust rough edges are explicitly addressed

## Phase guardrails

Use these checks before starting any step in this phase:

1. Does this work replace a prototype-safe assumption with a real local fact?
2. Does it preserve the existing `client -> worker -> cloud` responsibility split?
3. Can the result be surfaced truthfully in the GUI?
4. Would doing this out of order make a later step noisier or less honest?
5. Can the step be closed with a concrete completion note and proof artifact?

If the answer to most of these is no, it probably does not belong in Phase 2.
