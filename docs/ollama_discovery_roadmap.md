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

Goal:

- add one explicit client-facing seam for probing Ollama availability and enumerating local models

Exit criteria:

- the client has a discovery interface that can report Ollama availability and installed model ids
- the implementation is replaceable and does not leak shell details into the GUI

### Slice 2: Curated-versus-installed model view

Goal:

- combine the curated Modulo catalog with the discovered local model inventory

Exit criteria:

- the client can distinguish among unsupported, supported-but-not-installed, and installed-supported models
- the hosting setup surface reads from this combined state

### Slice 3: GUI discovery visibility

Goal:

- make local Ollama availability and model presence visible in the GUI

Exit criteria:

- the GUI can explain whether Ollama is available
- the GUI can show which curated models are present locally
- the language is user-facing rather than shell-oriented

## Completion note

Add a short summary here when complete:

- summary:
- proof added to repo:
