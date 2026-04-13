# Continue Consumer Roadmap

This mini roadmap covers the first clean external consumer path after the hosted private-scope proof became real.

It exists to make `Continue (VSCode)` the first non-OpenClaw consumer that Modulo can mount into through the existing shape-first `Mount` flow.

The goal is not to turn Modulo into a Continue-specific product.
The goal is to prove that Modulo can automate a real external consumer through the `OpenAI API` shape without breaking the generic `Shape -> Consumer -> staged edge changes` model.

This roadmap should be read alongside [platform_layering_spec.md](./platform_layering_spec.md).

## Goal

- treat `Continue (VSCode)` as a first-class consumer under the `OpenAI API` shape
- preserve the existing shape-first mount binding model
- automate only the narrow Continue config needed to point at a Modulo-managed OpenAI-compatible endpoint
- keep rollback and user trust in scope from the beginning

## Why this matters

- OpenClaw is already meaningful, but it is not a clean second proof because some installs are heavily customized
- Continue is a simpler external consumer target for validating the mount abstraction
- if Modulo can cleanly automate one second consumer, the `Mount` layer starts becoming real instead of conceptual
- this is the right level of productization after the shared hosted path is proven

## Planned slices

### Slice 1: Continue consumer registry entry

Goal:

- add `Continue (VSCode)` to the existing `Mount` consumer registry for the `OpenAI API` shape

Done when:

- `Continue (VSCode)` appears only for the compatible shape
- the mount summaries stay truthful about what exists versus what is still staged
- tests cover the new shape-to-consumer binding

Notes:

- this slice should not pretend config automation already exists
- the product truth should stay explicit that the consumer binding is ready before the file mutation flow lands

Status: completed

Completion note:

- summary:
  - added `Continue (VSCode)` as a first-class consumer under the `OpenAI API` shape without disturbing the existing OpenClaw path
  - updated mount summaries so Continue reads like a real staged consumer binding rather than falling through generic copy
  - preserved the shape-first binding model, where adding consumers should not break other consumer mappings
- proof added to repo:
  - `src/modulo/gui/controller.py`
  - `tests/test_gui_controller.py`

### Slice 2: Continue config contract and file ownership

Goal:

- define exactly what part of Continue config Modulo owns and how it will write it safely

Done when:

- the repo has a narrow Continue config contract for the Modulo-managed entry
- backup and rollback behavior are defined before real writes happen
- Modulo does not implicitly take ownership of the user's entire Continue config file

Notes:

- the safest shape is a Modulo-managed model entry or block, not whole-file ownership
- this slice is contract-first, not yet full GUI polish

Status: completed

Completion note:

- summary:
  - added a dedicated Continue discovery and config contract so Modulo now has a stable place to track config presence, managed-entry identity, and whether a Continue config already points at Modulo
  - defined narrow file ownership for the future apply flow, including the managed Continue entry, owned fields, and backup target path before any real file writes landed
  - tightened the `Mount` truth so Continue now reads as a staged contract with explicit config and backup details instead of looking falsely ready
- proof added to repo:
  - `src/modulo/client/continue_discovery.py`
  - `src/modulo/client/app.py`
  - `src/modulo/gui/controller.py`
  - `tests/test_client_worker.py`
  - `tests/test_gui_controller.py`

### Slice 3: Continue apply and rollback flow

Goal:

- make Modulo able to apply and undo the Continue mount cleanly

Done when:

- Modulo can back up the existing Continue config
- Modulo can add or update a Continue entry pointing at the local Modulo mount endpoint
- Modulo can remove or restore only what it owns during unmount/rollback
- tests cover create, update, and rollback cases

Notes:

- this slice should favor safety and reversibility over clever config mutation

Status: pending

### Slice 4: Mount UX truth pass for Continue

Goal:

- make the `Mount` surface explain Continue setup and state clearly enough for a real user

Done when:

- `Mount` shows whether Continue is:
  - not staged
  - ready to apply
  - configured
  - needs attention
- the user can understand what Modulo will change before apply
- the user can see how to recover or unmount without opening raw config files

Notes:

- this slice should stay product-shaped, not dashboard-shaped

Status: pending

## Completion note

Add a short summary here when the roadmap is complete:

- summary:
  - Modulo can now bind, apply, and roll back a Continue consumer through the `OpenAI API` shape without taking over the user's full Continue config
- proof added to repo:
  - `src/modulo/client/...`
  - `src/modulo/gui/...`
  - `tests/...`
