# Modulo Platform Layering Spec

This is a product-shape document, not an implementation roadmap.

It defines the canonical UI and system layering model for Modulo so development stays aligned with the intended product feel as the platform deepens.

## Core principle

> Shallow by default, deep by permission.

Modulo should:

- hide complexity at the surface
- expose truth only when requested
- avoid forcing infrastructure thinking on the user

The release goal remains tray-first.
The current GUI can continue to act as a richer second-layer proving surface, but it should not harden into a dashboard-first product.

## Layer overview

### Layer 0: Background runtime

User visibility: none

Responsibilities:

- node discovery
- model aggregation
- routing decisions
- worker health monitoring
- hosting lifecycle
- shim mounting
- version and protocol handling

Constraints:

- deterministic
- stable
- zero required user interaction

### Layer 1: System tray

User visibility: always

Purpose:

- glanceable system state
- immediate control

Primary truths:

- `Host`
- `Use`
- `Scopes`
- `Health`

Primary actions:

- use model
- host toggle
- join scope
- mute scope
- open panel

Constraints:

- no configuration
- no infrastructure language
- readable in under two seconds

### Layer 2: Tray popup / quick panel

User visibility: frequent

Purpose:

- fast interaction without opening the full UI

Capabilities:

- model selection grouped by scope
- quick mount
- join or mute scopes
- lightweight availability signals such as warm state and latency

Explicitly not primary here:

- node counts
- routing details
- provider exposure

### Layer 3: Focused utility windows

User visibility: occasional

Purpose:

- guided workflows without becoming a control center

Examples:

- host setup
- mount configuration
- scope management
- update handling

Constraints:

- one purpose per window
- minimal required decisions
- no persistent dashboard behavior

### Layer 4: Main utility window

User visibility: occasional

Purpose:

- expanded operational visibility

Candidate surfaces:

- `Use`
- `Host`
- `Scopes`
- `Diagnostics`

Constraints:

- no deep configuration by default
- no overwhelming controls
- treat this layer as the second surface, not the primary product

### Layer 5: Advanced / power controls

User visibility: rare, opt-in only

Purpose:

- expose deeper control for power users without polluting the default experience

Examples:

- mount details
- shim selection
- capability overrides
- warm retention policy
- concurrency limits

Constraints:

- hidden behind `Advanced`
- must not leak upward into Layers 1 through 3

### Layer 6: Debug / truth layer

User visibility: very rare

Purpose:

- expose system truth for debugging and trust

Examples:

- route trace
- logs
- worker registry truth
- raw execution state

This layer exists to:

- validate system behavior
- build trust
- debug edge cases

## Core product abstractions

The primary user-facing abstractions should remain:

### Host

What am I running?

### Use

What model am I using?

### Mount

Where am I using it?

### Scopes

Where do models come from?

### Health

Is it working?

## Explicit non-goals for primary layers

These should not surface in the primary product layers:

- provider selection
- routing strategy choices
- node counts by default
- infrastructure topology
- protocol details

Users should choose models, not evaluate systems.

## Scope model

The friendly user-facing source model remains:

- `Local`
- `Private`
- `Public`
- `Cloud`

Scopes should support:

- active
- muted
- deleted

The client should eventually treat scopes as known entities that can be:

- surfaced
- muted
- forgotten
- policy-restricted

That means the UI can stay simple while the backend keeps stricter scope and policy enforcement underneath.

## Model aggregation rule

Identical models should collapse into a single visible entry.

Multiple backing workers should remain invisible redundancy unless a deeper truth layer is opened.

The user should see:

- `gemma4:e4b   warm   ~120ms`

Not:

- counts of nodes or providers
- routing pool breakdowns

## Adapter boundary

Internally, Modulo should continue to think in Modulo-native contracts.

That means:

- scopes surface available models
- routing selects an eligible path
- adapters shape egress for provider- or consumer-specific expectations

This keeps provider-specific behavior at the boundary instead of leaking it into the main product model.

## Mount UX rule

Every mount should eventually produce a usable local endpoint that is:

- visible
- copyable
- optionally auto-copied

Future one-click integrations such as OpenClaw or editor tooling should build on that mount abstraction rather than replace it.

## Design test

Every feature should be checked against:

1. Does this remove user thinking?
2. Does this improve reliability?
3. Does this improve speed?
4. Can this be automated instead?

If the answer is no, it should be rejected or pushed deeper into the stack.

## Current fit with the repo

Most of the current direction already fits this model:

- `Use` and `Host` are already becoming the primary verbs
- diagnostics and route truth are already being pushed downward instead of upward
- scope-aware model-source language is already replacing singular `network` assumptions
- the client remains supervisory while routing and truth stay in shared contracts and the cloud layer

## Future refactor candidates

These ideas fit the product well, but should be treated as future shape changes rather than silently hardened now:

- a true tray-first shell replacing the current main-window-first experience
- a dedicated `Scopes` surface instead of burying scope behavior only inside `Use`
- a first-class `Mount` abstraction in the client UX
- moving `Debug` and deeper diagnostics further away from the main default shell

These are not rejections.
They are reminders to evolve toward the target shape deliberately rather than accidentally.

## Final rule

> If the user has to think about infrastructure, the design failed.

Modulo should not feel like:

- a dashboard
- a marketplace console
- a generic control panel

Modulo should feel like:

- a capability that quietly exists
- a tray-presence utility
- something as simple and immediately legible as old Hamachi felt in everyday use
