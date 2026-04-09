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

Status: completed

Summary:

- surfaced host model warm-state directly in the Host tab with a dedicated model-state line, summary, and compact runtime details
- kept the presentation scoped to host operations so warm-state truth does not leak into Buyer or Diagnostics
- verified both warm and cold cases through the GUI controller layer

Proof added to repo:

- GUI controller state now includes host warm-state badge, summary, and detail lines
- Host tab renders model state and compact loaded-model details alongside hosting readiness
- GUI tests cover warm default state and cold selected-model state

### Slice 3: Hosting prewarm lifecycle

Status: completed

Summary:

- added an optional host-side prewarm lifecycle that triggers when hosting starts or a live host switches models
- tracked prewarm state in the client so the Host tab can distinguish `warming`, `warm`, and `warm_failed` from simple loaded-model visibility
- kept failures operator-facing and normal by surfacing them as warm-state truth instead of letting warmup errors escape as raw exceptions

Proof added to repo:

- `HostingPrewarmResult` and `ClientHostingPrewarmer` in the client layer
- `LocalOllamaModelPrewarmer` in the prototype harness using Ollama prewarm requests against the selected host model
- client, prototype, and GUI tests covering successful prewarm and warm-failed host states

## Completion note

Add a short summary here when complete:

- summary: the Host side now shows both whether a model is loaded and whether Modulo explicitly warmed it as part of hosting lifecycle, which makes local resource use and cold-start avoidance much more transparent
- proof added to repo: warm-state lifecycle now spans loaded-model discovery, optional prewarm requests, Host-tab visibility, and automated coverage for success and failure paths
