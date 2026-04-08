# GUI Roadmap

This document is the working reference for how the physical Modulo GUI client should be built.

It exists to keep GUI work explicit, phased, and aligned with the current `client -> worker -> cloud` architecture rather than letting UI work drift into a second runtime.

## How to use this doc

- use the current GUI slice to decide what UI work should happen next
- add a short summary under a slice when it is completed
- keep GUI slices thin and demonstrable
- do not move runtime logic into the GUI just because the GUI needs to visualize it
- only add new GUI slices when they clearly strengthen the installable product path

## Product intent

The GUI client should become the physical local application a user installs to manage both buyer and hosting behavior.

The GUI is responsible for:

- sign-in and connection state
- onboarding flows
- OpenClaw connection controls
- hosting controls
- worker and smoke-test visibility
- user-visible activity, health, and simple model configuration

The GUI is not responsible for:

- routing decisions
- retry or lease behavior
- worker job protocol semantics
- execution logic
- cloud control-plane policy

Those remain in `cloud` and `worker`. The GUI should supervise, visualize, and guide.

## Current GUI phase

Current GUI phase: `Phase 0` planning and thin-client surface definition.

Current active GUI slice:

- define the GUI build path explicitly so future client work lands as coherent product slices instead of ad hoc frontend additions

Definition of progress for this phase:

- GUI work is documented as a separate roadmap
- GUI slices are ordered around the installable product path
- the GUI roadmap remains consistent with the backend roadmap and architecture guardrails

## Completed GUI slices

No GUI-specific slices are completed yet.

When GUI work begins, completed slices should follow the same format as the backend roadmap:

- `Status`
- short `Summary`
- short `Proof added to repo`

## Upcoming GUI slices

These are ordered to keep the GUI build coherent and consistent with the current architecture.

### GUI Slice 1: Client surface inventory and state map

Goal:

- turn the existing client supervision and onboarding data into an explicit GUI-facing state map

Why this slice matters:

- the GUI should start from real product state, not from visual mock logic
- it makes sure the first screens reflect what the client can already truthfully report

Exit criteria:

- document the first GUI screens and the state each one needs
- map existing client types such as onboarding status, smoke-test status, worker status, and hosting state to GUI concerns
- identify missing view-model or event seams without implementing full UI yet

### GUI Slice 2: Barebones local shell and app bootstrap

Goal:

- stand up the thinnest possible physical GUI shell that launches locally and can display real client state

Why this slice matters:

- it creates the installable app skeleton early
- it lets future GUI slices build on a real shell instead of on screenshots or notebooks

Exit criteria:

- choose and document the first GUI stack explicitly
- create an app shell that launches locally
- render at least one real client status view from live app state

### GUI Slice 3: Onboarding home screen

Goal:

- build the first home screen that shows connection, OpenClaw, hosting, worker health, and smoke-test state

Why this slice matters:

- this is the smallest honest version of the product
- it gives users one place to understand what Modulo is doing right now

Exit criteria:

- the home screen reads from real client state
- it clearly shows connected/disconnected and hosting enabled/disabled states
- it surfaces worker health and last smoke-test result

### GUI Slice 4: Hosting controls and worker panel

Goal:

- let the GUI start, stop, and restart hosting while showing worker activity and errors

Why this slice matters:

- it turns the GUI from a passive status screen into a real control surface
- it proves the GUI is supervising the worker rather than replacing it

Exit criteria:

- GUI buttons trigger the existing hosting control path
- worker state, last error, and recent activity are visible
- no worker runtime logic is duplicated in the UI layer

### GUI Slice 5: Smoke test and diagnostics panel

Goal:

- expose the smoke-test path and basic diagnostics in a clear GUI flow

Why this slice matters:

- smoke tests are one of the most important confidence tools for onboarding and support
- this gives the GUI a truthful debugging surface without needing advanced operator tooling

Exit criteria:

- user can run a smoke test from the GUI
- result state is clearly shown as pass/fail with useful text
- last worker error and last smoke-test output are visible in one place

### GUI Slice 6: OpenClaw connection flow

Goal:

- implement the GUI path for connecting OpenClaw from the client-facing app

Why this slice matters:

- this is core to the actual product promise
- it moves the GUI from local supervision toward the true onboarding story

Exit criteria:

- GUI can guide the user through the OpenClaw connection path
- success and failure states are visible and explicit
- the flow uses real client behavior, not GUI-only placeholders, whenever possible

### GUI Slice 7: Hosting setup flow

Goal:

- implement the GUI path for selecting a model, enabling hosting, and understanding local readiness

Why this slice matters:

- hosting is the second half of the product story
- it turns the app into a real contributor control surface

Exit criteria:

- GUI can guide a user through model selection and hosting enablement
- worker readiness and simple constraints are made visible
- the flow stays explicit and opt-in

### GUI Slice 8: Activity and continuity visibility

Goal:

- surface enough routing/activity information in the GUI to make behavior legible without turning the GUI into an operator console

Why this slice matters:

- users should be able to tell that Modulo is alive, where work is going, and whether continuity is helping
- this helps trust without leaking backend policy complexity into the interface

Exit criteria:

- GUI can show recent jobs or recent worker activity
- GUI can show simple routing/continuity hints when useful
- the presentation stays user-facing rather than internal-only

## GUI guardrails

Use these checks before starting a new GUI slice:

1. Does this slice strengthen the real installable product path?
2. Does it read from real client/worker/cloud state rather than inventing fake UI state?
3. Does it keep routing and execution logic outside the GUI?
4. Can it be demonstrated in a small, real interaction?
5. Would it still make sense if the backend contracts stayed exactly as they are today?

If the answer to most of these is no, it probably should not be the next GUI slice.

## GUI stack decision rule

The first GUI stack should be chosen for:

- fast local iteration
- easy packaging into a physical desktop app
- low friction when calling the existing Python client surface
- a clear path to tray-style behavior later

Do not pick a stack primarily for visual polish. Pick the one that lets the product become real fastest without forcing a rewrite of the supervision boundary.
