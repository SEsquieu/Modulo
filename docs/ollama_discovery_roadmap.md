# Ollama Discovery Roadmap

This mini roadmap covers the first major Phase 2 step: truthful local Ollama discovery.

It exists to replace the current curated-only hosting list with a real view of what is actually available on the user's machine.

## Goal

- detect whether Ollama is installed and reachable
- discover locally installed models
- intersect local inventory with Modulo's curated catalog
- expose that state through the client and GUI without moving shell or runtime logic into the widgets

## Why this matters

- hosting setup is not trustworthy until the app knows what is actually installed
- GUI guidance should distinguish between supported, installed, and ready
- later readiness and execution work should be based on facts, not curated defaults alone

## Planned slices

### Slice 1: Local Ollama discovery seam

Status: completed

Summary:

- added a replaceable client-facing Ollama discovery seam that can probe local command availability and enumerate installed model ids
- wired the default prototype path to use the new discovery seam so discovery state is available through the normal client status flow
- kept discovery logic out of the GUI and exposed it through hosting setup state instead

Proof added to repo:

- `OllamaDiscovery` and `OllamaDiscoveryStatus` in the client layer
- default prototype wiring through the client supervisor
- discovery and client tests covering model parsing and hosting setup state

### Slice 2: Curated-versus-installed model view

Status: completed

Summary:

- combined the curated Modulo catalog with discovered local Ollama inventory in the client hosting setup state
- taught the hosting setup surface to distinguish supported-and-installed, supported-but-missing, and installed-but-not-curated models
- updated the hosting setup guidance so “ready” now depends on whether the selected curated model is actually present locally

Proof added to repo:

- richer hosting setup state in the client supervisor
- hosting setup panel now shows the overlap between curated and installed models
- client and GUI tests covering installed-versus-curated model distinctions

### Slice 3: GUI discovery visibility

Status: completed

Summary:

- surfaced Ollama availability and discovered inventory as first-class GUI state in the hosting setup flow
- added a dedicated Ollama status readout so the GUI can explain local discovery before the user interprets hosting readiness
- kept the presentation user-facing by summarizing local availability and curated overlap instead of exposing shell-level details

Proof added to repo:

- explicit Ollama summary and inventory state in the GUI controller
- hosting setup panel now shows Ollama availability and inventory summary directly
- GUI tests covering local Ollama visibility and curated overlap summaries

## Completion note

Add a short summary here when complete:

- summary:
- proof added to repo:
