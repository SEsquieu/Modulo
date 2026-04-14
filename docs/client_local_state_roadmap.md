# Client Local State Roadmap

This mini roadmap defines the first persistent client-side storage layer for Modulo.

It exists because consumer automation should not mutate user-facing config files without a durable, Modulo-owned place to keep:

- backup files
- rollback metadata
- managed-entry ownership records
- lightweight local telemetry and recovery breadcrumbs

This roadmap should be read alongside [platform_layering_spec.md](./platform_layering_spec.md) and [continue_consumer_roadmap.md](./continue_consumer_roadmap.md).

## Goal

- add one narrow Modulo-owned local state directory on the client machine
- make consumer-side config backups and rollback metadata depend on that state directory
- define a safe place for lightweight local telemetry without overbuilding a metrics system
- keep the storage surface boring, explicit, and easy to reason about

## Why this matters

- automatic consumer configuration needs trustworthy rollback
- backups should live in Modulo-owned persistent state, not only beside third-party config files
- future local telemetry should have a stable home before more automation lands
- this is a prerequisite for real Continue apply and rollback work

## Design guardrails

- one Modulo-owned root directory only
- narrow ownership
- explicit per-consumer backup metadata
- no silent broad cleanup behavior
- no assumption that Modulo owns whole third-party config files

The client-local state directory should eventually be able to hold shapes like:

- `backups/`
- `mounts/`
- `telemetry/`
- a small state manifest for owned entries and rollback targets

This does not mean building a full analytics system.
It means creating the minimum persistent foundation that future automation can trust.

## Planned slices

### Slice 1: Client state root contract

Goal:

- define where Modulo client state lives on disk and what top-level directories it owns

Done when:

- the repo has one explicit client-local state contract
- the client can resolve a Modulo-owned state root on the local machine
- backup, mount, and telemetry areas have reserved locations even if they are still empty
- tests cover path resolution and directory intent without relying on the current workstation

Notes:

- keep platform-specific path logic narrow
- this slice is contract-first, not yet full write flow

Status: completed

Completion note:

- summary:
  - added a dedicated client-local state resolver that reserves one Modulo-owned root plus `backups`, `mounts`, `telemetry`, and manifest paths without writing anything yet
  - exposed that contract through shared client status so future consumer automation can depend on one stable local-state seam
  - kept the slice contract-first and workstation-agnostic with path-resolution coverage
- proof added to repo:
  - `src/modulo/client/local_state.py`
  - `src/modulo/client/app.py`
  - `tests/test_client_local_state.py`

### Slice 2: Backup and rollback metadata seam

Goal:

- make consumer backup planning point at Modulo-owned client state instead of ad hoc sidecar files

Done when:

- Continue and future consumers can resolve a durable backup target inside Modulo state
- rollback metadata has a defined home separate from third-party config files
- managed-entry identity can be persisted without implying whole-file ownership
- tests cover backup-target resolution and stored ownership records

Notes:

- prefer simple files and explicit metadata over clever indirection

Status: completed

Completion note:

- summary:
  - moved Continue backup planning into Modulo-owned client state instead of leaving it beside third-party config
  - added an explicit rollback metadata path under the reserved `mounts` area so future apply and rollback work have a stable record location
  - surfaced the new storage truth through both client status and mount guidance without introducing real file writes yet
- proof added to repo:
  - `src/modulo/client/app.py`
  - `src/modulo/gui/controller.py`
  - `tests/test_client_worker.py`
  - `tests/test_gui_controller.py`

### Slice 3: Lightweight local telemetry seam

Goal:

- reserve a safe place for local event breadcrumbs and recovery-oriented telemetry

Done when:

- the client has a defined telemetry storage location
- telemetry intent is scoped to local recovery and trust, not a full reporting system
- future mount/apply flows can record small local events without inventing new storage paths
- tests cover file layout and safe defaults

Notes:

- do not overbuild analytics here
- this slice is about stable storage, not dashboards

Status: pending

### Slice 4: Consumer roadmap dependency alignment

Goal:

- make downstream consumer automation explicitly depend on the client-local state layer

Done when:

- `Continue` apply/rollback work points at the new client-local state seam
- docs and handoff clearly describe consumer automation as contingent on this layer
- Mount truth stays honest about what is staged versus what is durable

Notes:

- this slice is mostly alignment and dependency cleanup

Status: pending

## Completion note

Add a short summary here when the roadmap is complete:

- summary:
  - Modulo now has one boring, durable client-local state directory for backups, rollback metadata, and lightweight local telemetry
  - consumer apply/rollback work now depends on that storage seam instead of inventing per-consumer persistence ad hoc
- proof added to repo:
  - `src/modulo/client/...`
  - `tests/...`
