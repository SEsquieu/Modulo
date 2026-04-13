# Route Trace Visibility Roadmap

This mini roadmap covers the next focused work after the private MVP proof.

It exists to make the now-real shared execution path explainable without turning Modulo into a dashboard-first product.

The goal is not to surface every internal router fact at the top level.
The goal is to preserve a tray-first product direction while giving the second-layer GUI enough truth to answer:

- where a request went
- why it went there
- what scope/source applied
- whether retries, filtering, or fallback changed the outcome

## Goal

- surface truthful routed-execution visibility for operators and developers
- keep top-level `Use` and `Host` surfaces light
- place route depth in the second-layer GUI where it can help debugging and trust
- preserve the `Local / Private / Public / Cloud` direction without hardening the wrong UI assumptions

## Why this matters

- Modulo now has a real end-to-end request/response across separate real networks
- once remote execution is real, explainability becomes more valuable than adding more hidden behavior
- route-trace truth is the best next step for debugging, trust, and future policy work
- this can happen cleanly before Windows packaging resumes

## Planned slices

### Slice 1: Route-trace client contract

Goal:

- define the client-facing route-trace shape that the GUI can consume without depending on raw cloud internals

Done when:

- the client can carry a structured latest-route-trace summary
- the shape includes source, scope, selected worker, route reason, retries, and final outcome
- the contract leaves room for filtered-worker detail without forcing it into the top-level shell

Notes:

- this slice is about shape, not visual polish
- keep the contract narrow enough for the second-layer GUI

Status: completed

Completion note:

- summary:
  - added a dedicated client-facing route-trace state model plus filtered-worker detail shape
  - threaded the latest route-trace summary into `ClientStatus` without coupling the GUI to raw cloud internals
  - left the fetch seam provider-based so local prototype and hosted targets can share one later trace path
- proof added to repo:
  - `RouteTraceStatus` and related client-facing trace dataclasses in `src/modulo/client/app.py`
  - `ClientStatus.latest_route_trace` and optional `ClientRouteTraceProvider` seam in `src/modulo/client/app.py`
  - client integration coverage in `tests/test_client_worker.py`

### Slice 2: Prototype and hosted trace fetch path

Goal:

- expose recent route-trace truth through the existing client/session/debug path

Done when:

- the prototype harness can fetch the latest route trace for the active routed request path
- the hosted/shared target can surface the same trace shape
- tests prove the trace survives successful and failed routed execution

Notes:

- prefer one truthful fetch path over duplicated local-only and remote-only logic

Status: completed

Completion note:

- summary:
  - added one shared latest-trace fetch shape for both local prototype and hosted targets
  - exposed the latest routed execution through a dedicated control-plane read endpoint instead of GUI-only state
  - taught the prototype harness to carry latest route-trace truth through the same active target flow used for shared visibility
- proof added to repo:
  - `GET /api/platform/trace/latest` in `src/modulo/cloud/http.py`
  - `LocalPrototypeRouteTraceProvider` in `src/modulo/prototype.py`
  - latest-trace payload helpers in `src/modulo/client/app.py`
  - HTTP and prototype coverage in `tests/test_http_app.py` and `tests/test_prototype.py`

### Slice 3: Diagnostics route-trace view

Goal:

- surface route-trace visibility in the second-layer GUI without bloating the top-level fabric

Done when:

- `Diagnostics` includes a route-trace view that shows the latest routed execution clearly
- the view explains source, scope, selected worker, route reason, and final outcome
- retries and filtered-worker detail are available, but not forced into the main shell surface

Notes:

- this should feel like the existing `Smoke / Activity / Errors` pattern, not a new dashboard

Status: completed

Completion note:

- summary:
  - added a dedicated Route tab inside Diagnostics so latest routed execution is visible one layer down from the main shell
  - surfaced route result, summary, and detailed trace facts without pushing route verbosity into top-level `Use` or `Host`
  - kept the Diagnostics structure aligned with the existing nested-tab shell pattern instead of introducing a new dashboard surface
- proof added to repo:
  - Diagnostics Route view in `src/modulo/gui/window.py`
  - route-trace controller state in `src/modulo/gui/controller.py`
  - GUI controller coverage in `tests/test_gui_controller.py`

### Slice 4: Operator trust pass

Goal:

- tighten wording and summaries so route traces help real humans understand what happened

Done when:

- the route-trace view uses stable operator-facing language
- the latest route summary can support both success and failure cases
- the top-level shell stays simple while deeper trace truth remains one layer down

Notes:

- this slice is where we make the route-trace surface actually pleasant to use
- avoid dumping raw internal objects into the GUI

Status: completed

Completion note:

- summary:
  - tightened the Diagnostics Route wording so the latest trace reads like an operator-facing explanation instead of a raw internal dump
  - added stable success and failure summaries that explain source, scope, worker selection, retries, and no-route outcomes in human terms
  - translated filtered-worker reasons into clearer skip language while keeping the deeper trace truth one layer down in Diagnostics
- proof added to repo:
  - operator-friendly route summary/detail helpers in `src/modulo/gui/controller.py`
  - GUI controller coverage for both successful and failed routed traces in `tests/test_gui_controller.py`

## Completion note

Add a short summary here when the roadmap is complete:

- summary:
  - added a dedicated client-facing route-trace contract
  - exposed latest route traces through local prototype and hosted fetch paths
  - surfaced route visibility in Diagnostics with a final trust pass for operator-friendly success and failure wording
- proof added to repo:
  - `src/modulo/client/app.py`
  - `src/modulo/cloud/http.py`
  - `src/modulo/prototype.py`
  - `src/modulo/gui/controller.py`
  - `src/modulo/gui/window.py`
  - `tests/test_client_worker.py`
  - `tests/test_http_app.py`
  - `tests/test_prototype.py`
  - `tests/test_gui_controller.py`
