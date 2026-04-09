# Private Networks Design Note

This is a platform-shape document, not an implementation roadmap.

The goal is to workshop how access-controlled internal Modulo networks should fit the base platform before any slices are planned. This should not be bolted on after the public-network model is already cemented.

## Why this matters

An enterprise often has a large amount of lightly used hardware that is already inside the organization's trust boundary:

- HR laptops and desktops
- executive or admin machines
- departmental workstations
- internal edge devices

If Modulo can form an access-controlled private network across that fleet, the enterprise pitch becomes much stronger:

- `data privacy`: prompts and outputs can remain inside the organization's boundary
- `cloud spend reduction`: low-duty-cycle internal workloads can be absorbed by existing machines
- `no new capex`: the first adoption motion uses hardware the org already owns

This is a fundamentally different product shape than "public marketplace only."

## Product stance

Modulo should eventually support three routing domains:

1. `local`
2. `private network`
3. `public network / trusted cloud`

That means the platform cannot assume all non-local traffic belongs to a single public pool.

Private networks should feel first-class, not like a policy wrapper around the public network.

## Core idea

A private network is an org-scoped pool of:

- hosts
- users
- policies
- model visibility
- routing authority
- auditability

The most important property is that the private network is a trust boundary, not just a filter.

That trust boundary should affect:

- which hosts can advertise into the pool
- which users can route into the pool
- which models are visible
- which jobs can cross org boundaries
- which usage and ledger events are attributed to that org

## Architectural fit

Private networks touch nearly every major platform layer:

### Client

The client session bridge will eventually need org-aware platform truth, such as:

- current org membership
- visible private-network models
- routing scope
- role-based permissions
- internal credit or quota posture

This suggests the session bridge should stay broad enough to carry org and policy context, not just buyer/use state.

### Host

The host side will eventually need enrollment into a specific routing domain:

- local-only
- private org network
- public network

This should be explicit. "Hosting enabled" alone is not rich enough long term.

The host contract will likely need future fields for:

- org or network membership
- visibility scope
- policy tags
- attestation / trust posture

### Router / control plane

The router will need to reason about scope before it reasons about best-fit worker selection.

A likely future order of operations:

1. resolve request scope
2. restrict eligible workers by scope and policy
3. apply trust and health filtering
4. prefer warm / leased / high-score workers
5. emit auditable route reason

This is important: org scope should become part of route eligibility, not just decoration on a chosen route.

### Registry

The worker registry will eventually need to distinguish among:

- worker identity
- worker trust
- worker scope
- worker visibility

That suggests a future model where worker advertisements are not globally visible by default.

### Session / account / ledger

Private networks will eventually need org-aware accounting:

- usage attribution
- quotas or internal credits
- department or team policy
- audit and reporting

This should not live inside the router itself, but the router and ledger layers will need a shared concept of org scope.

## Design principles

These should guide future work:

### 1. Scope before optimization

The platform should first decide what pool a request is allowed to use, then optimize within that pool.

### 2. Visibility is policy

Model visibility is not just a UI problem. A model that belongs to a private network should not leak into public discovery surfaces by accident.

### 3. Hosts must opt into scope explicitly

A host should knowingly contribute to:

- only local usage
- a private org network
- the public network

This should never be inferred silently.

### 4. Session truth must become org-aware

The session bridge is the right home for future org membership, role, network visibility, and policy state.

### 5. Public and private should share core mechanics, not duplicated systems

The platform should not fork into two unrelated routing stacks. The same core worker/routing/health model should support multiple scopes.

## What this likely changes in current assumptions

Several current assumptions are okay for prototype work, but should not harden too far:

### "Network" is singular

Today the UI and platform often talk about "the network" as if there is one pool. Long term, that likely becomes:

- local
- private network
- public network
- cloud

### Buyer/use routing is mostly public-platform-shaped

Eventually the Use tab will need to make room for scoped visibility:

- models I can use locally
- models I can use inside my org
- models I can use publicly
- models I can use from trusted cloud providers

### Host visibility is globally meaningful

Eventually a host's advertised models may only be meaningful inside an org boundary.

## Non-goals for now

This note is not yet deciding:

- exact auth implementation
- enterprise SSO shape
- org admin console design
- precise quota/credit rules
- deployment topology
- how public and private billing will differ

Those belong in later design or roadmap documents.

## Open questions

These deserve deeper architectural discussion before implementation:

1. Is org scope attached to the user session, the request, or both?
2. Can one host participate in multiple private networks, or is scope one-to-one per host?
3. Should private-network model listings be fully isolated, or optionally bridgeable through explicit policy?
4. How should hybrid fallback work when a private network has no healthy worker for a requested model?
5. What is the minimum trust and enrollment model for a host to join an org-scoped pool?
6. How much of this needs to exist in the first enterprise-capable version versus a later policy layer?

## Recommended next move

Before planning implementation slices, write one follow-up design doc that narrows:

- org and network identity model
- host enrollment model
- scoped routing model
- visibility and discovery rules
- fallback policy between local, private, public, and cloud

That should come before any roadmap for private-network implementation.
