# Private Scope MVP Design

This is a narrowing doc for implementation, not a full long-term architecture spec.

Its job is to make the next execution proof safe to build without hardening the wrong assumptions around `network` scope.

## Why this doc exists

Modulo now has two competing truths:

- the current implementation and GUI still carry some older `local / network / cloud` language
- the newer product direction is `Local / Private / Public / Cloud`

That gap is still recoverable, but only if the next remote-execution proof is built with scope-aware eligibility in mind.

The immediate MVP is not "public marketplace execution."

The immediate MVP is:

**one machine can route a request through Modulo to a model hosted on another non-local worker through a bounded private platform scope, using the same router and worker contract that later private networks will rely on**

## Product-facing source model

The product-facing source vocabulary should remain:

1. `Local`
2. `Private`
3. `Public`
4. `Cloud`

For the next implementation proof:

- `Private` is the correct conceptual home for the first bounded remote-execution proof
- `Public` does not need to exist functionally yet
- `Cloud` remains a future fallback and trust anchor
- older `network` language may still appear in implementation seams, but new routing assumptions should not depend on one singular network pool
- a local-network environment is only one early way to validate `Private`, not the definition of it

## Scope governance principle

Support for a scope and permission to use that scope are not the same thing.

Modulo should treat scope as policy-clamped, not self-declared.

That means:

- the platform may support `Public`
- a private organization or bounded private network may still forbid `Public`
- a host may request to advertise into `Public`
- the actual routable result should still be limited to what policy allows

In other words, routing should use an `effective scope`, not just an advertised scope.

## Effective scope model

The long-term shape should leave room for four related truths:

- `requested_scope`
- `advertised_scope`
- `max_allowed_scope`
- `effective_scope`

For the MVP, not all four need to be fully implemented as named fields yet, but the architecture should preserve room for them.

The intended behavior is:

1. the client or host requests a scope
2. platform and private-boundary policy decide the maximum allowed scope
3. the worker registration is clamped to that maximum
4. the router only ever sees the effective result

This keeps the router simple while still making scope trustworthy.

## Policy layers

The clean release model should assume scope may be constrained by multiple layers:

- platform policy
- private-network or org policy
- host policy
- user or client preference

The effective scope should be the intersection of those layers, not the union.

Example:

- the broader Modulo platform supports `Public`
- a private team network disables `Public`
- a developer workstation tries to host publicly
- the effective result is still `Private`

This is how a bounded team environment can stay private even when the product later supports global scope elsewhere.

## MVP scope stance

The next proof should behave as if the platform already understands:

- local-only execution
- one non-local private scope
- future room for public scope later

That means the router should move toward:

1. resolve allowed scope
2. restrict eligible workers to that scope
3. apply health, trust, warm-state, and continuity logic inside that scope
4. emit a route trace that explains what happened

The router should not treat all non-local workers as one permanent pool.

## Concrete MVP target

The near-term MVP proof is:

1. one machine runs the Modulo cloud/API
2. that same machine can also be used for an initial local end-to-end proof
3. a second machine can run a worker bridge against the cloud/API inside the same bounded private environment
4. the worker advertises a locally available Ollama model
5. a use-side request hits the cloud router
6. the router assigns work to the remote private-scope worker
7. the worker executes through its local Ollama runtime
8. the response comes back through the same control-plane path

If that works reliably, Modulo has proven the true remote execution path without needing packaging first.

That environment may be:

- one office LAN
- a VPN-connected set of devices
- a geographically distributed org-scoped private pool

What makes it `Private` is the access-controlled Modulo boundary, not physical proximity.

## Single-machine proof before cross-machine proof

It is reasonable to prove this on one machine first, as long as the boundaries stay real.

That single-machine proof is valid if:

- the request still goes through the cloud/router
- the worker still registers and claims through the worker transport seam
- the execution still happens through the worker runtime contract
- the route trace still reflects a non-trivial router decision

The important thing is not "two physical machines first."
The important thing is "the chain really hits the router and the external worker seam."

## Scope model for the next slices

The minimum scope model should be small and explicit.

### Request scope

For the near-term proof, a request should carry or resolve to one of:

- `local`
- `private`
- `cloud`

`public` can remain reserved for later, but the model should leave room for it.

### Worker scope

A worker should explicitly advertise its serving scope.

For the near-term proof that means:

- `private`

Later it may include:

- `public`
- additional private pool identity

Worker scope should remain subject to policy clamp before it becomes active routing truth.

### Visibility rule

A request should only see workers whose scope is compatible with the selected source.

For now:

- `private` requests may use `private` workers
- `local` requests should not silently route to non-local workers
- `cloud` should stay explicit and future-facing

Later, `public` requests may use `public` workers, but only when that worker's effective scope is actually public.

## Minimal private identity model

Do not overbuild org semantics yet.

For the MVP, the private boundary can be represented with a lightweight identifier such as:

- `private_network_id`

That ID should be available to:

- the request/session context
- the worker advertisement
- the router eligibility filter
- future route traces and ops views

This keeps the platform from assuming all private workers belong to one global pool.

## Host enrollment model

Hosts must opt into their serving scope explicitly.

For the near-term MVP that means the host path should be able to say:

- host locally only
- host into a private network

Even if the UI keeps this lightweight at first, the underlying contract should not infer it silently.

On release, hosts should also default to the safest non-global scope.

That means:

- new hosts should default to `Private`, not `Public`
- `Public` should require explicit opt-in
- a private-network policy should be able to forbid `Public` entirely
- invalid scope escalation should be rejected or clamped during registration, not only filtered later during routing

## Route trace requirement

The next remote-execution work must collect enough route data to support future operator visibility.

This is not optional polish.

If private networks are going to be operationally trustworthy, an operator or admin machine needs a rich route trace similar to network-ops diagnostics.

The route trace should eventually make it possible to answer:

- what source was requested
- what scope was resolved
- what private network or boundary applied
- which workers were considered
- why workers were filtered out
- which worker was selected
- why the selected worker won
- whether continuity or warm-state influenced the choice
- whether retry or rehome happened
- what the final execution outcome was

## Minimum route trace shape

The exact schema can evolve later, but the next slices should preserve data for fields like:

- `trace_id`
- `request_id`
- `buyer_id`
- `selected_source`
- `resolved_scope`
- `private_network_id`
- `requested_model_id`
- `eligible_worker_ids`
- `filtered_worker_reasons`
- `selected_worker_id`
- `route_reason`
- `continuity_used`
- `warm_path_used`
- `retry_count`
- `final_status`
- `final_error`
- `timestamps`

That data can begin as in-memory structured trace state if needed. It does not need a finished dashboard before the private-scope MVP is proven.

## Ops visibility principle

The router should emit structured route facts now so future ops surfaces can be built on preserved truth instead of reconstructed guesses.

That means:

- do not rely only on free-form strings
- preserve both machine-readable reason codes and operator-friendly summaries
- keep trace generation inside the cloud/router path, not spread across client widgets

## What not to build yet

Do not turn this into a full enterprise feature pass yet.

Still out of scope for the MVP:

- full org administration
- SSO
- multi-pool membership
- policy editor UI
- quota and billing model
- a dedicated ops dashboard application

## Recommended implementation stance

The next build slices should assume:

- bounded private-scope remote execution is the true MVP proof
- that proof conceptually belongs to `Private`
- route eligibility should become scope-aware before broader routing work continues
- route tracing should be captured alongside the MVP so private-network ops does not require a large retrofit later

## Resulting next move

Use this doc as the architectural guardrail for the next implementation roadmap:

- [private_mvp_roadmap.md](./private_mvp_roadmap.md)
