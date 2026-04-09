# Host Warm-State Roadmap

This mini roadmap covers the next host-side refinement slice before packaging work.

It exists to make hosting behavior visible and trustworthy by showing whether the selected model is actually loaded, warming, warm, or failed to warm on the local machine.

## Goal

- expose truthful local warm-state visibility for the selected host model
- make resource allocation legible to the host operator
- optionally prewarm the selected host model when hosting starts
- keep all of that state on the Host side without coupling it to Buyer or OpenClaw setup

## Why this matters

- a host should be able to tell whether enabling hosting actually loaded a model
- a host should understand why RAM or VRAM is currently in use
- “hosting enabled” and “model warm” are different truths and should be shown separately
- packaging a light client makes more sense after the host experience feels operationally honest

## Planned slices

### Slice 1: Ollama loaded-model discovery seam

Status: completed

Summary:

- added a client-facing loaded-model discovery seam that reads the local Ollama `/api/ps` state
- threaded loaded-model visibility into hosting setup status with a warm-state badge, summary, and compact runtime facts
- kept the change in the client/prototype seam so the Host tab can consume it later without embedding Ollama logic in widgets

Proof added to repo:

- `OllamaLoadedModelsDiscovery`, `OllamaLoadedModelsStatus`, and `LoadedOllamaModel` in the client layer
- hosting setup state now includes warm-state badge, summary, details, and loaded-model ids
- client, prototype, and loaded-model discovery tests covering warm and cold host states

### Slice 2: Host GUI warm-state visibility

Status: in progress

Goal:

- represent host model state clearly in the Host tab
- show a compact runtime details block for loaded-model metadata

Done when:

- the Host tab shows a clear state such as `COLD`, `WARMING`, `WARM`, or `FAILED`
- the Host tab shows a concise runtime detail panel for the selected model

Proof added to repo:

- 

### Slice 3: Hosting prewarm lifecycle

Status: not started

Goal:

- optionally prewarm the selected host model when hosting starts
- track warmup transitions and failures explicitly

Done when:

- hosting start can trigger a lightweight prewarm poke for the selected model
- the client and GUI reflect `warming`, `warm`, and `warm_failed` truthfully
- warmup failures are surfaced as normal operator-facing state instead of raw exceptions

Proof added to repo:

- 

## Completion note

Add a short summary here when complete:

- summary:
- proof added to repo:
