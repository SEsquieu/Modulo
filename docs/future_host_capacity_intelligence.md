# Future Host Capacity Intelligence

This note preserves a future routing and hosting concept that should stay in scope for later platform iterations without being forced into the current MVP contracts.

## Why this matters

Modulo will eventually need richer host capability truth than:

- what model is active right now
- whether the worker is healthy right now

As routing grows more sophisticated, the platform should understand the difference between:

- models that are installed but currently cold
- models that are warm and immediately rentable
- models that can warm reliably but slowly
- models that technically load but do not fit or remain stable well on a host

That richer truth can support:

- dynamic idle swapping between warm and cold models
- smarter routing between warm-path preference and better-fit cold-path promotion
- better trust weighting for hosts beyond simple success/failure history
- future host-side earnings and efficiency policy decisions
- more truthful operator visibility for private networks

## Core idea

A host should eventually be able to advertise:

1. its currently warm active model
2. its broader installed model inventory
3. capability and benchmark facts about each installed model

That does **not** mean every installed model should immediately become a first-class routing target in the current MVP.

Instead, the likely shape is:

- the client or worker builds a local capability profile over time
- the host keeps that profile locally as the source of truth
- the platform can request or receive selected portions of that profile when needed
- routing later uses that data as advisory capacity intelligence rather than as the first eligibility gate

## Dynamic idle swapping concept

One future router/host behavior worth preserving is dynamic idle swapping.

High-level flow:

1. a host may keep one model warm because it is the best current demand fit
2. that same host may also advertise additional cold installed models
3. if demand changes, the router may choose to target a cold installed model on that host
4. the host may then spin down an idle warm model to make room for warming the requested cold model
5. the platform should preserve trace facts explaining that this happened

This should eventually let Modulo trade off:

- immediate warm availability
- warm-up delay
- residency fit quality
- host stability
- expected value of keeping the current model resident versus swapping it out

## Candidate per-model profile fields

The future local host profile may include fields like:

- `installed`: whether the model is present on the machine
- `warmable`: whether the model has successfully warmed at least once under current conditions
- `last_warm_success_at`: most recent successful warm timestamp
- `warm_time_ms`: observed warm-up duration
- `residency_fit`: how well the model fits the host's available resources
- `idle_unload_behavior`: how the model tends to unload when left idle
- `generation_throughput`: later, a rolling throughput measure

Recommended early normalization for `residency_fit`:

- `full_fit`
- `split_fit`
- `cpu_only`
- `unstable`
- `failed`

Recommended early normalization for `idle_unload_behavior`:

- `sticky`
- `eventually_unloads`
- `unloads_fast`
- `unknown`

Other future useful fields may include:

- `last_failure_reason`
- `last_benchmark_at`
- `warm_success_rate`
- `median_first_token_ms`
- `median_tokens_per_second`
- `preferred_keepalive_window`

## Where this profile likely belongs

This profile should probably begin as a **client-built or worker-built local profile**, not as an always-on core routing contract.

That means:

- the local client or worker can benchmark or observe host behavior over time
- the local machine can persist the richer profile privately
- the worker heartbeat can publish a compact summary when useful
- the control plane can request richer profile data on demand later

This is probably better than forcing all of the future benchmark fields into the base worker registration schema immediately.

The base worker contract should stay focused on:

- identity
- serving scope
- current healthy/claimable state
- actively advertised routing models

The richer host-capacity profile can stay adjacent to that contract until the router is ready to use it.

## Plausible publish model

One reasonable future shape:

1. the client builds or refreshes the local model profile in the background
2. the worker heartbeat publishes only compact routing-relevant facts by default
3. the cloud can ask for richer profile detail when:
   - a host is being evaluated for a difficult route
   - an operator requests diagnostics
   - the router is considering a cold-model swap
4. the route trace records when capability intelligence influenced a routing choice

That keeps normal control-plane chatter light while still preserving the possibility of richer scheduling later.

## Relationship to routing

This future profile should influence routing in later stages, but should not replace the current routing basics.

The likely future order is:

1. scope eligibility
2. health and current claimability
3. continuity and warm-path preference
4. host capacity intelligence
5. economic or degradation policy

Examples of later routing questions this profile could answer:

- should we keep this request on a warm but slower model path?
- should we cold-promote a better-fit installed model on this host?
- should we avoid a host whose recent warm attempts are unstable?
- should we prefer a host whose idle unload behavior is stickier for bursty workloads?

## Relationship to route traces

If this idea is implemented later, route traces should preserve facts like:

- whether a host was considered warm-capable or only cold-capable
- whether a warm-to-cold swap was requested
- whether an idle resident model was intentionally unloaded
- which capability or benchmark facts influenced the decision
- whether the route won because of warm-state, fit quality, throughput, or stability history

This will matter for both operator diagnostics and long-term trust ranking.

## Current stance

This is **not** a current MVP requirement.

For now, this note exists to preserve the architectural shape so later routing work does not forget:

- installed inventory is not the same thing as active warm inventory
- warm-path intelligence should eventually become dynamic
- the client may be the right place to build rich host capability truth locally
- heartbeats or on-demand fetches can publish that truth to the network when appropriate
