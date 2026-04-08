# Session Bridge Roadmap

This mini roadmap covers the client-owned session bridge layer that should exist whenever the Modulo UI is running.

It is distinct from the worker bridge:

- the `session bridge` is an always-on client control-plane sync layer
- the `worker bridge` is a hosting/runtime layer used for routed inference when hosting is enabled

## Goal

- create one client-owned control-plane seam that starts with the UI
- fetch platform truth needed by both buyer and host surfaces
- keep buyer discovery independent from hosting runtime state
- prepare a stable place for future account, credit, and routing-config reads

## Why this matters

- buyer-visible network and cloud model lists are dynamic and should not be hardcoded
- hosting and buyer routing should share platform truth without sharing runtime state
- future credit balance, account state, and buyer config should come from one client-owned layer
- this is the clean place for fetch/sync behavior before real OpenClaw integration begins

## Planned slices

### Slice 1: Session bridge contract

Goal:

- add a dedicated client-side session/control-plane interface and state model

Exit criteria:

- the client can hold session-bridge-backed platform state separately from worker state
- the bridge shape is explicit about fetching and syncing, not inference execution

### Slice 2: Prototype platform fetch path

Goal:

- back the session bridge with a prototype-safe control-plane fetch path

Exit criteria:

- the client can fetch buyer-visible platform data without enabling hosting
- the bridge can return placeholder platform state truthfully through the client surface

### Slice 3: Buyer-facing network model discovery

Goal:

- fetch buyer-visible network/cloud model options through the session bridge

Exit criteria:

- the buyer side of the client can display a truthfully fetched model list
- model inventory no longer depends on static client assumptions

### Slice 4: Session-backed client sync

Goal:

- route more client-owned status through the session bridge

Exit criteria:

- the client has one obvious place for future account, credits, and buyer config reads
- host and buyer tabs can share platform truth without coupling their workflows

## Completion note

Add a short summary here when complete:

- summary:
- proof added to repo:
