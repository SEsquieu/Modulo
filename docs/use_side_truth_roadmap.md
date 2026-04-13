# Use-Side Truth Roadmap

This mini roadmap covers the next focused work after route-trace visibility is complete.

It exists to make the `Use` side of Modulo truthful about what a person can actually use, where that request will go, and what is still only staged or conceptual.

The goal is not to build a giant chooser or a dashboard-first model marketplace.
The goal is to keep the tray-first product direction intact while making the second-layer `Use` surface honest and easy to trust.

This roadmap should be read alongside [platform_layering_spec.md](./platform_layering_spec.md).
The `Use` side is part of the second-layer proving surface today, but it should evolve toward a tray-first model where scopes group models cleanly and deeper truth stays below the surface.

## Goal

- make the `Use` tab truthful about `Local / Private / Public / Cloud`
- keep model-source language simple and consumer-readable
- separate visible model availability from allowed routing policy
- treat scopes as known groupings that can later become active, muted, or deleted
- keep top-level `Use` flow light while pushing deeper detail into nested sections

## Why this matters

- the shared path is now real across separate networks
- the current `Use` surface shows the right shape, but some of its truth is still prototype-safe or mixed together
- model source visibility will eventually drive both user trust and policy enforcement
- the `Use` side should move toward grouped scopes with nested model lists, not a flat marketplace browser
- this is the cleanest next step before productization resumes

## Planned slices

### Slice 1: Use-source contract tightening

Goal:

- define a sharper client-facing `Use` state shape around visible model sources and active routing truth

Done when:

- the client has a stable way to describe what is visible under `Local / Private / Public / Cloud`
- the contract distinguishes:
  - visible models
  - selected model
  - active route
  - route policy constraints
- the contract makes room for known-scope state without forcing scope management into the top-level UI yet
- the GUI no longer needs to infer source truth from mixed OpenClaw or host state

Notes:

- keep the contract narrow and user-facing
- avoid locking in enterprise-heavy naming at the UI layer

Status: completed

Completion note:

- summary:
  - added a dedicated `Use`-side client contract so source visibility, selected model truth, and route-policy truth no longer have to be inferred from mixed platform and OpenClaw state
  - grouped the current client-facing sources under `Local / Private / Public / Cloud`, including room for future scope state such as mute/delete without forcing that UI yet
  - made the contract explicitly distinguish visible models from allowed routing so the client can be honest even when support is partial or staged
- proof added to repo:
  - `UseModelOption`, `UseScopeStatus`, `UseRouteStatus`, and `UseSideStatus` in `src/modulo/client/app.py`
  - `ClientStatus.use` plus grouped source construction in `src/modulo/client/app.py`
  - contract coverage in `tests/test_client_worker.py`

### Slice 2: Private/shared visibility fetch truth

Goal:

- make `Use` visibility reflect the active platform target more truthfully for local and shared/private sources

Done when:

- local installed models are clearly separated from remotely visible shared models
- private/shared model visibility follows the active platform target instead of stale local assumptions
- scoped visibility can be grouped under known sources instead of flattened into one network list
- empty states explain whether nothing is visible because:
  - no models are available
  - no shared hosts are advertising
  - the current source is not yet supported

Notes:

- prefer one truthful fetch path over duplicated local-only versus remote-only logic

Status: completed

Completion note:

- summary:
  - taught the session-bridge and control-plane visibility fetch path to speak more directly in `Private / Public / Cloud` terms while preserving the older network-model field for compatibility
  - added active-target awareness and per-source visibility summaries so the client can explain why shared sources are empty or unavailable without guessing
  - kept `Public` intentionally empty and policy-reserved while making `Private` truth follow the active platform target for both local and remote reads
- proof added to repo:
  - richer `PlatformSessionStatus` source visibility fields in `src/modulo/client/app.py`
  - local and remote session-bridge fetch updates in `src/modulo/prototype.py`
  - control-plane status payload updates in `src/modulo/cloud/http.py`
  - coverage in `tests/test_client_worker.py`, `tests/test_prototype.py`, and `tests/test_http_app.py`

### Slice 3: Use tab truth pass

Goal:

- reshape the `Use` tab so model choice is front and center while route truth stays visible and low-noise

Done when:

- the primary `Use` card clearly shows:
  - selected model
  - selected source
  - active route target
  - provider/path truth
- nested `Route / Local / Private / Public / Cloud` sections feel consistent with the rest of the shell
- grouped scope presentation can later collapse naturally into tray popup behavior without a redesign
- dead copy and staged/prototype-heavy phrasing are buried or removed from the default view

Notes:

- keep the top-level `Use` flow calm enough that it still points toward the eventual tray-first release

Status: completed

Completion note:

- summary:
  - rewired the `Use` UI to read from the dedicated `Use` contract instead of stitching together older buyer/network/OpenClaw fields
  - grouped source visibility into `Route / Local / Private / Public / Cloud` sections so the shell now matches the product-facing source model more closely
  - kept the active route card and selector simple while burying deeper route and source truth under nested sections
- proof added to repo:
  - `Use`-side controller state and grouped source helpers in `src/modulo/gui/controller.py`
  - `Use` tab section updates in `src/modulo/gui/window.py`
  - GUI controller coverage in `tests/test_gui_controller.py`

### Slice 4: Policy and empty-state trust pass

Goal:

- make `Use` source visibility trustworthy when policy, scope, or incomplete support changes what is actually available

Done when:

- the `Use` tab explains why a source is unavailable without sounding broken
- private/public/cloud language stays simple while preserving stricter backend meaning
- muted or restricted scopes have a clean future path without changing the model-source vocabulary again
- the current state supports future policy hardening without rewriting the `Use` UI again

Notes:

- this slice is about trust wording and policy-aware truth, not deep authorization implementation

Status: in progress

Completion note:

- summary:
- proof added to repo:

## Completion note

Add a short summary here when the roadmap is complete:

- summary:
- proof added to repo:
