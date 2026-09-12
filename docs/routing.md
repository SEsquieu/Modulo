# Routing

Routing belongs to the Modulo control plane. Workers advertise facts; clients submit intent; neither independently chooses a remote execution target.

## Request inputs

A chat request carries:

- exact `model_id`
- execution mode: `local`, `network`, or `cloud`
- optional explicit scope: `local`, `private`, `public`, or `cloud`
- optional `private_network_id`
- buyer identity for short-lived continuity
- streaming and tool requirements
- routing policy selection

If no explicit scope is supplied, the current mapping is:

| Execution mode | Resolved scope |
| --- | --- |
| `local` | `local` |
| `network` | `private` |
| `cloud` | `cloud` |

## Eligibility

For the requested mode, a worker is rejected when:

- its worker kind does not match;
- it is unhealthy;
- its effective scope does not match;
- its private-network identifier does not match an explicitly constrained private request;
- it does not advertise the exact requested model;
- its current load meets or exceeds maximum concurrency;
- it was excluded after an earlier failed attempt.

Each rejection is retained as a structured `FilteredWorkerReason` in the route trace.

A private network identifier is only a routing boundary in the current alpha. It is not authentication.

## Score

Eligible workers are ranked using the current score:

```text
score =
    confidence          * 0.50
  + recent_success_rate * 0.35
  + (1 - timeout_rate)  * 0.10
  + headroom            * 0.05
```

where `headroom = max(max_concurrency - current_load, 0)`.

This is deliberately legible rather than learned. The inputs are runtime facts carried in the worker's advertised model state.

## Continuity and fallback

The control plane can retain a short-lived lease keyed by buyer and model. A leased worker is only preferred while it remains eligible. The goal is to reduce cold-start churn without bypassing scope, health, model, or capacity policy.

Under the current v1 policy, a `network` request may fall back to a trusted cloud worker only when no network worker is eligible, the policy allows fallback, and the cloud worker advertises the exact requested model.

Modulo does not silently substitute models.

## Trace

A route trace records:

- request model, buyer, mode, scope, and private network
- eligible worker IDs
- every filtered worker and reason
- selected worker and reason code
- continuity/warm-path use
- job and attempt identity
- retry count
- current and final status
- final error

The trace is currently stored in memory and is an observability aid, not a durable audit log.

