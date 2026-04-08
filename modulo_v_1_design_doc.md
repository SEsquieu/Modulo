# Modulo v1 Design Doc

## Goal

Ship the smallest version of Modulo that proves one thing end to end:

**A user can install Modulo, connect OpenClaw with one explicit action, select a Modulo network model, and talk to a model hosted on a remote worker machine with no hand edits.**

Everything in v1 serves that goal.

## Platform thesis

Modulo is a **trust-weighted execution platform**.

Its job is to route a request onto the execution path most likely to deliver the experience the user expects:

- `Local` when the user wants privacy and direct control
- `Network` when the user wants low-cost distributed execution
- `Cloud` when the user wants curated first-party reliability

Over time, Modulo should earn the right to move more traffic onto `Network` by proving that requests succeed and behave as advertised. As network trust grows, first-party cloud overhead should fall.

## Non-goals for v1

Do not build these yet:

- credit economy sophistication
- dynamic pricing
- capability abstraction
- fallback model families
- peer-to-peer networking
- mesh routing
- regional coordinators
- worker auto-optimization beyond basic safe suggestions
- plugin-based native Modulo provider for OpenClaw
- full analytics or fancy dashboarding
- dynamic model substitution policies
- capability-tier routing UI
- automated cost optimization across execution modes

## Product constraints

### User trust constraints

- Installing Modulo must **not** mutate OpenClaw automatically.
- Installing Modulo must **not** start contributing hardware automatically.
- Worker contribution must be explicit opt-in.
- OpenClaw connection must be explicit opt-in.
- No hand edits to OpenClaw config are allowed in the happy path.

### UX constraints

- Buyer capability is available as soon as Modulo is installed and signed in.
- OpenClaw connection happens from a single obvious action inside Modulo.
- Worker enablement happens from a single obvious action inside Modulo.
- Modulo should feel unobtrusive and local-first.

## Core product promise

**Install Modulo. Click Connect OpenClaw. Pick a network model. Your OpenClaw agent now runs on the Modulo network.**

Secondary promise:

**Click Enable hosting to earn. Modulo will help you host a supported local model and contribute it to the network.**

Long-term framing:

**Modulo should eventually give users explicit execution trust levels: `Local`, `Network`, and `Cloud`.**

In v1, `Network` is the path to prove. `Cloud` should still be treated as the future reliability anchor, and `Local` should remain a first-class future mode even if it is lightly represented at launch.

## Platform principles

These principles should shape decisions even when the related features are deferred:

1. **Route by trust, not just availability.**
2. **Make execution location legible to the user.**
3. **Earn flexibility only after earning predictability.**
4. **Treat first-party cloud as a trust anchor and fallback path.**
5. **Design for graceful degradation, but do not surprise the user.**

## Development principles

These principles should shape implementation order, not just architecture:

1. **Build vertical slices that prove the roadmap, not isolated ideas.**
2. **Keep `client` and `worker` aligned through shared contracts and supervision boundaries.**
3. **Prefer one real end-to-end path over multiple partial surfaces.**
4. **Do not canonize ad hoc ideas unless they clearly improve the core proof path.**
5. **Treat every slice as preparation for the one demo that proves v1.**

## Future extensibility targets

Modulo should leave room for these later platform capabilities without forcing them into v1:

- execution policies such as `strict`, `balanced`, `economy`, or `fast`
- curated model equivalence and downgrade rules
- policy-driven fallback across `Local`, `Network`, and `Cloud`
- cost, latency, and trust-aware routing preferences
- clearer privacy and execution provenance controls

---

# 1. High-level system shape

## External surfaces

### 1. Modulo client
The user-facing local app responsible for:
- sign-in
- local environment detection
- OpenClaw connection
- worker enablement
- local status
- minimal controls

### 2. Modulo cloud API
The public ingress responsible for:
- Ollama-compatible API surface for OpenClaw
- routing requests to workers
- worker registration and health tracking
- job lifecycle management
- result normalization

### 3. Modulo worker bridge
A local background process on contributor machines responsible for:
- detecting local supported models
- registering with Modulo cloud
- heartbeating health
- polling for jobs
- executing requests via local Ollama
- returning results

## Internal core roles

### Coordinator / Router
Responsible for:
- maintaining worker registry
- maintaining model-to-worker lookup
- tracking worker health
- assigning jobs to workers
- handling timeouts/retries/fallback

### Worker registry
Tracks:
- worker identity
- models served
- capacity
- current load
- health metadata

### Job system
Tracks:
- incoming requests
- assignments
- completion/failure
- timeout/retry state

---

# 2. OpenClaw integration strategy

## Ground truth

For v1, Modulo must present itself to OpenClaw as a **remote Ollama-compatible host** using the native Ollama API shape. OpenClaw's docs indicate that Ollama integration uses the native `/api/chat` path, and that remote setup should use a custom Ollama base URL rather than the `/v1` OpenAI-compatible path. Native Ollama is the documented path that preserves streaming and tool calling. ([docs.openclaw.ai](https://docs.openclaw.ai/providers/ollama?utm_source=chatgpt.com))

## Why this matters

We do **not** want OpenClaw to know or care that Modulo is a distributed router. To OpenClaw, Modulo should look like a normal Ollama host.

## v1 OpenClaw contract

Modulo must implement the minimum Ollama-native endpoints OpenClaw expects:

- `POST /api/chat`
- `GET /api/tags`
- optional `POST /api/show`

OpenClaw configuration should point `models.providers.ollama.baseUrl` to Modulo's endpoint. Existing OpenClaw config can contain a non-empty `baseUrl` that wins during merge, so Modulo cannot blindly rerun onboarding on an existing install; it must detect and intentionally switch the target. ([docs.openclaw.ai](https://docs.openclaw.ai/concepts/models?utm_source=chatgpt.com))

## v1 OpenClaw setup behavior

The Modulo client should:
1. Detect whether OpenClaw is installed.
2. Detect whether OpenClaw is already configured.
3. If fresh, use automated onboarding against Modulo's Ollama-native endpoint.
4. If already configured, patch/switch the relevant provider target explicitly.
5. Run a smoke test.
6. Only then report success.

OpenClaw provides `openclaw onboard --non-interactive` with custom Ollama base URL and model support, which Modulo can wrap. ([docs.openclaw.ai](https://docs.openclaw.ai/cli/onboard?utm_source=chatgpt.com))

## User-facing OpenClaw controls in Modulo client

### Primary action
- `Connect OpenClaw`

### After connected
- model selector for network model
- simple mode selector:
  - Network
  - Local only
  - Hybrid (future; optional in v1)

For v1, Network mode is enough. Local only can be added if easy.

## Execution mode framing

Modulo should eventually expose three execution destinations:

- `Local`: execute on the user's own machine
- `Network`: execute on trust-qualified distributed workers
- `Cloud`: execute on Modulo-managed curated infrastructure

In v1, Modulo only needs to make `Network` real in the OpenClaw happy path. But the client and router should avoid assumptions that make `Local` and `Cloud` awkward to add later.

---

# 3. Client design

## Client responsibilities

The Modulo client is the single user-facing entry point.

It must:
- feel small and local
- not require config file editing
- own onboarding flows
- keep worker setup simple

## Client state model

### Default state after install
- signed in / connected to Modulo account
- buyer-active
- OpenClaw untouched
- worker inactive

### Explicit actions
- `Connect OpenClaw`
- `Enable hosting to earn`

## First-launch screen

Minimal version:

- status: connected to Modulo
- status: OpenClaw not connected / connected
- status: Hosting disabled / enabled
- `Connect OpenClaw`
- `Enable hosting to earn`

No mode fork. No buyer-vs-worker wizard.

## OpenClaw connect flow

### Goal
No manual edits.

### Flow
1. User clicks `Connect OpenClaw`.
2. Client detects OpenClaw.
3. Client asks user to choose a Modulo model from available network models.
4. Client applies config safely.
5. Client runs a test request through OpenClaw/Modulo.
6. Client shows success or error.

### Success condition
OpenClaw can successfully send a request to Modulo and receive a valid response.

## Worker enable flow

### Goal
Simple, explicit opt-in.

### Flow
1. User clicks `Enable hosting to earn`.
2. Client detects Ollama installation.
3. Client detects existing local supported models.
4. If none exist, client may recommend a model based on hardware and offer install.
5. User confirms model(s) to host.
6. Client starts worker bridge.
7. Client registers worker and models.
8. Client shows hosting enabled.

### Worker recommendations
Basic only. For v1:
- detect GPU/VRAM if possible
- suggest one safe supported model
- show approximate download size
- require confirmation before pulling the model

Never silently download multi-GB models.

## Client architecture

### Components
- UI shell (desktop app or CLI wrapper)
- local control service or internal module
- OpenClaw integration module
- Ollama integration module
- worker bridge supervisor
- Modulo cloud API client

### Practical v1 implementation advice
Fastest path is likely:
- one local app/binary
- one background worker thread/process for bridge behavior
- minimal local persistence

---

# 4. Network API design

## Public ingress role

The Modulo cloud API must act as a **network-backed Ollama host** for OpenClaw and as the control plane for workers.

Longer term, the same ingress should also support policy-driven routing decisions across `Local`, `Network`, and `Cloud`, even if only the network path is implemented at first.

## Public Ollama-compatible endpoints

### `GET /api/tags`
Returns the list of network-available models.

### `POST /api/chat`
Accepts an Ollama-native chat request and routes it to a suitable worker.

### Optional `POST /api/show`
Returns model metadata if needed.

## Worker control endpoints

### `POST /worker/register`
Register a worker and its metadata.

### `POST /worker/heartbeat`
Report worker health and current load.

### `POST /worker/jobs/claim`
Worker asks for a job.

### `POST /worker/jobs/{job_id}/result`
Worker submits result.

### `POST /worker/jobs/{job_id}/fail`
Worker reports execution failure.

## Authentication

### Buyer/OpenClaw side
- API token managed by Modulo client
- token attached to Modulo-hosted Ollama endpoint calls

### Worker side
- worker token issued by Modulo

## Pull model for workers

Workers should poll for jobs rather than receive inbound pushes. This avoids NAT and firewall issues and keeps deployment easy.

Worker loop:
1. register
2. heartbeat
3. claim job
4. execute locally
5. return result
6. repeat

---

# 5. Request/response contracts

## Public chat request contract

Modulo should accept the Ollama-native chat shape as closely as practical.

Example:

```json
{
  "model": "llama3.1:8b",
  "messages": [
    {"role": "user", "content": "Explain Modulo simply."}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 256
  }
}
```

## Internal job shape

Normalized job object:

```json
{
  "job_id": "job_123",
  "model": "llama3.1:8b",
  "messages": [
    {"role": "user", "content": "Explain Modulo simply."}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 256
  },
  "timeout_s": 60
}
```

## Worker result contract

```json
{
  "job_id": "job_123",
  "status": "completed",
  "response": {
    "model": "llama3.1:8b",
    "message": {
      "role": "assistant",
      "content": "Modulo is a distributed network for model execution."
    },
    "done": true,
    "prompt_eval_count": 42,
    "eval_count": 19
  },
  "timing": {
    "run_ms": 1830
  }
}
```

If failure:

```json
{
  "job_id": "job_123",
  "status": "failed",
  "error": {
    "code": "EXEC_TIMEOUT",
    "message": "Execution timed out"
  }
}
```

## Result normalization requirement

Workers may vary. Modulo must guarantee that the response returned to OpenClaw is always valid and correctly shaped.

**OpenClaw should not be able to tell it is not talking to a real Ollama host.**

That means Modulo must normalize:
- structure
- token/usage fields
- done/final markers
- tool call fields when present
- streaming chunks when implemented

---

# 6. Routing design

## v1 routing goal

Do the simplest possible correct thing.

Given model X:
1. find workers that advertise model X
2. filter unhealthy workers out
3. filter overloaded workers out
4. choose the best remaining worker
5. if none exist, optionally fallback to trusted infra if available
6. otherwise return unavailable

This is the first version of a broader rule:

**Route to the most trusted eligible execution target for the selected mode and policy.**

## v1 worker selection logic

Use a simple score:
- healthy
- model present
- lowest current load
- recent success ratio
- lowest recent timeout rate

No regions, no pricing, no mesh.

## Long-term routing direction

The future router should be able to weigh more than worker availability. It should eventually reason about:

- execution mode: `Local`, `Network`, `Cloud`
- trust score by `(worker, model)` history
- exact model identity and compatibility
- latency and success-rate expectations
- fallback policy selected by the user
- cost posture such as `economy` vs `strict`

This does **not** mean building capability abstraction in v1. It means keeping the architecture compatible with policy-driven routing later.

## High-value routing continuity behavior

High-value next-step behavior for the router:

- preserve buyer continuity when a conversation is active
- avoid cold-start thrash on follow-up requests
- keep warm workers warm for short-lived active sessions
- break continuity automatically when health, timeout, or load conditions require it

The best abstraction for this is a **short-lived buyer lease** on a worker for a specific model.

The intent is not to give buyers permanent worker ownership. The intent is to let the router prefer a recently warm, recently successful execution path long enough to protect UX.

For v1 and early demos, this should be treated as a high-value routing behavior because it improves:

- response continuity
- perceived speed
- cold-start avoidance
- realism of the end-to-end proof

The lease must stay **soft**:

- reuse the leased worker while it remains healthy and under capacity
- refresh the lease on activity
- expire the lease after a short idle timeout
- break the lease on repeated timeout, explicit failure, overload, or stale heartbeat

This belongs in the `cloud` router and control plane, not in the client or worker bridge. Workers should report facts. The router should decide whether continuity is still worth preserving.

## Trusted fallback

Strongly recommended:
run at least one trusted internal worker or dev node for:
- smoke testing
- reliability during bootstrap
- fallback when network is sparse

This worker uses the exact same worker bridge protocol.

Longer term, this trusted fallback naturally becomes the seed of the `Cloud` execution path.

---

# 7. Worker bridge design

## Role

The worker bridge is the network-side runtime adapter between Modulo cloud and local Ollama.

It does not own agent logic. It only owns:
- registration
- health
- job polling
- local execution
- result return

## Responsibilities

- discover local supported models
- register enabled models
- heartbeat capacity/load
- claim jobs
- call local Ollama
- submit results
- pause/stop when requested locally

## Worker config

Minimal v1 config:

```yaml
modulo_url: https://api.modulo.ai
worker_token: secret
enabled_models:
  - llama3.1:8b
max_concurrency: 1
```

Optional later:
- CPU/GPU utilization ceilings
- schedule windows
- pause on user activity

## Worker lifecycle

### Startup
1. read config
2. verify Ollama reachable
3. detect enabled local models
4. register worker
5. enter loop

### Loop
1. send heartbeat
2. claim job if capacity available
3. execute job via local Ollama
4. return result or failure
5. repeat

### Shutdown
- mark worker unavailable
- stop claiming new jobs

---

# 8. Health and reliability model

## Why this matters

The most important network quality signal is whether a worker consistently completes jobs correctly for a given model.

More broadly, the platform's core asset is its ability to predict whether a given execution target will satisfy the user's expectation for that model and mode.

## v1 worker health dimensions

Track per `(worker_id, model_id)`:
- jobs_assigned
- jobs_completed
- jobs_failed
- timeouts
- avg_latency_ms
- recent_success_rate
- current_load
- last_heartbeat_at

## v1 health rules

### Healthy if
- heartbeat fresh
- completion rate above threshold
- timeout rate below threshold
- current load below concurrency limit

### Unhealthy if
- heartbeat stale
- repeated recent failures
- too many timeouts

## v1 confidence score

Keep it simple:

`confidence = completion_rate - timeout_penalty - failure_penalty`

This does not need to be exposed to users yet. It is only for routing.

In future versions, confidence should evolve into a trust signal that can influence cross-mode fallback and policy-aware routing, not just worker ranking inside the network.

## Cold start

New worker/model pairs start at neutral confidence and receive low-risk traffic.

---

# 9. Failure handling

## Hard requirement

OpenClaw should experience reliable behavior even if workers are flaky.

Future requirement:

Modulo should eventually support **graceful degradation** when the user explicitly permits it. That means preserving user intent under constraint instead of only succeeding or failing.

## v1 failure handling rules

### Timeout
If a worker claims a job and does not complete within timeout:
- mark failure
- penalize worker health
- retry once on another worker if available
- otherwise fail cleanly

### Worker failure
If worker returns explicit failure:
- record failure
- retry once if another worker exists

### Malformed result
If result does not validate:
- reject result
- mark worker failure
- retry once if possible

### No worker available
Return model unavailable cleanly.

### Deferred future fallback behavior

Not for v1, but important to anticipate:

- `strict` policy: exact model or fail
- `balanced` policy: exact model preferred, trusted equivalent allowed
- `economy` policy: cheaper lesser model may be allowed if the user opted in

Any fallback to a different model must be policy-driven and never surprising.

## Smoke test requirement

When connecting OpenClaw, the Modulo client must run a live test through the same path users will rely on.

---

# 10. Minimal persistence/data model

## Tables / collections

### users
- id
- auth identity
- api token ref

### models
- model_id
- display_name
- enabled
- ollama_runtime_name
- canonical_model_identity

### workers
- worker_id
- user_id
- status
- max_concurrency
- current_load
- last_heartbeat_at
- metadata_json

### worker_models
- worker_id
- model_id
- enabled
- jobs_assigned
- jobs_completed
- jobs_failed
- timeouts
- avg_latency_ms
- confidence
- runtime_identity
- trust_notes

### jobs
- job_id
- user_id
- model_id
- request_json
- status
- assigned_worker_id
- created_at
- claimed_at
- completed_at
- response_json
- error_json

This is enough for v1.

---

# 11. Onboarding and setup state machines

## A. Fresh install state machine

1. Install Modulo client
2. Sign in
3. Modulo client shows:
   - Connect OpenClaw
   - Enable hosting to earn
4. User clicks Connect OpenClaw
5. Client detects OpenClaw and configures it against Modulo
6. Client runs smoke test
7. Success shown

## B. Existing OpenClaw install state machine

1. User clicks Connect OpenClaw
2. Client detects existing OpenClaw config
3. Client reads current relevant provider target
4. Client switches target to Modulo safely
5. Client runs smoke test
6. Success shown

Existing config cannot be blindly overwritten because non-empty `baseUrl` in OpenClaw agent `models.json` can win during merge. ([docs.openclaw.ai](https://docs.openclaw.ai/concepts/models?utm_source=chatgpt.com))

## C. Worker enablement state machine

1. User clicks Enable hosting to earn
2. Client checks Ollama availability
3. Client checks supported local models
4. If none, suggests one supported model and asks for install confirmation
5. User confirms
6. Client starts bridge and registers worker
7. Success shown

---

# 12. Open questions to resolve before build

These are the most important unknowns or ambiguous areas still left in the design. They should be resolved before or during early implementation so the build stays coherent.

## A. Model identity and compatibility

### Question
What exactly counts as "the same model" on the Modulo network?

### Why it matters

The platform cannot build trust if two workers advertise the same name but return materially different behavior.

### Decisions needed

- Is identity based only on the Ollama tag such as `llama3.1:8b`?
- Do we require an exact digest, Modelfile fingerprint, or curated canonical identity?
- Are different quantizations considered the same model or different models?
- What minimum compatibility standard is required before a worker can advertise a model?

### Recommended initial answer

For v1, treat model identity conservatively. Use a curated supported-model list and require exact named model matches, with room to add stronger fingerprinting later.

## B. Supported model policy

### Question
Which models are allowed on the network in v1?

### Why it matters

An open-ended model catalog makes routing, QA, and trust much harder.

### Decisions needed

- Will v1 support one model, a small curated list, or any Ollama model?
- Which models are approved for worker hosting?
- Which models are exposed to OpenClaw buyers?
- Do we separate "network supported" from "cloud curated" models later?

### Recommended initial answer

Start with one to three curated models maximum. Do not allow arbitrary worker-advertised models in the happy path.

## C. Privacy and trust posture

### Question
What privacy guarantees is Modulo making when requests run on network workers?

### Why it matters

Execution location is one of the main trust boundaries in the platform.

### Decisions needed

- Are prompts stored by default anywhere in the system?
- Can network workers see raw prompt content?
- Are users clearly told when execution leaves their machine?
- Do some request classes need to be blocked from `Network` later?
- What distinction will exist between `Network` and `Cloud` in user-facing privacy language?

### Recommended initial answer

Be explicit that `Network` means execution may occur on third-party or community hardware. Minimize retention, document the trust boundary clearly, and avoid making stronger privacy claims than the system can enforce.

## D. Authentication and tenant isolation

### Question
How are buyer requests, worker actions, and internal control-plane operations authenticated and isolated?

### Why it matters

This is foundational platform infrastructure, not a polish concern.

### Decisions needed

- What token type does OpenClaw use when calling Modulo?
- How are worker tokens issued, rotated, and revoked?
- How are users isolated from each other's jobs and worker state?
- Can a worker only claim jobs it is eligible to serve?
- What server-side checks prevent job spoofing or result injection?

### Recommended initial answer

Use separate buyer and worker credentials from day one. Assume every worker is untrusted except for authenticated protocol compliance.

## E. Streaming support in v1

### Question
Is true Ollama-compatible streaming in scope for v1, or is v1 non-streaming first?

### Why it matters

Streaming is a major compatibility and UX factor, but it also adds complexity across routing, retries, and normalization.

### Decisions needed

- Must `POST /api/chat` support streaming in the first end-to-end demo?
- If streaming fails mid-response, what should Modulo do?
- Should the smoke test use streaming or non-streaming?

### Recommended initial answer

Prove non-streaming first. Add streaming only after the basic request path is stable, unless OpenClaw usability makes it impossible to defer.

## F. Tool calling compatibility

### Question
How much tool-calling compatibility is truly required for OpenClaw to feel correct?

### Why it matters

Tool-calling inconsistencies can break trust even if simple chat works.

### Decisions needed

- Is tool calling part of the v1 definition of done?
- Are only plain chat flows required at first?
- What model/runtime combinations are allowed if tool support is inconsistent?

### Recommended initial answer

Do not assume tool calling is solved just because native Ollama paths are used. Treat it as a separate compatibility milestone unless proven otherwise during Phase 0.

## G. Trusted fallback design

### Question
What is the minimum first-party fallback footprint needed to keep the platform reliable during bootstrap?

### Why it matters

The network will not earn trust if early requests fail whenever supply is sparse.

### Decisions needed

- Will v1 always have at least one Modulo-operated worker?
- Is fallback best-effort or part of the expected happy path?
- When no trusted fallback exists, what exact user-facing error should appear?

### Recommended initial answer

Treat at least one trusted first-party worker as required for early development and demos, even if the future product emphasizes distributed supply.

## H. Routing policy boundaries

### Question
What should the router be allowed to do automatically in v1, and what must remain explicit?

### Why it matters

Trust depends on predictable semantics.

### Decisions needed

- Can the router retry on another worker automatically? Yes, likely.
- Can the router fallback from `Network` to trusted first-party infra automatically? Probably yes if still serving the exact same model.
- Can the router substitute a different model? No for v1.
- Can the router change execution mode without explicit user policy? No.

### Recommended initial answer

Allow retries and exact-model trusted fallback. Do not allow silent model substitution or silent mode changes in v1.

## I. Client implementation shape

### Question
What form should the first Modulo client take?

### Why it matters

The wrong client shape can slow everything down before the platform proves value.

### Decisions needed

- Desktop app, CLI-first app, or hybrid?
- Is there a background service/daemon in v1, or just a launched helper process?
- What local persistence is actually needed for v1?

### Recommended initial answer

Bias toward the fastest installable local app that can own onboarding and worker enablement reliably. Prefer simplicity over polish.

## J. Worker capability and hardware policy

### Question
How much hardware introspection and gating is needed before allowing a worker to host a model?

### Why it matters

Poor hardware-fit decisions will show up as timeouts, flakiness, and loss of trust.

### Decisions needed

- What minimum hardware checks are required?
- Do we allow CPU-only workers in v1?
- Do we require a local benchmark or just basic heuristics?
- How is `max_concurrency` set safely?

### Recommended initial answer

Use conservative heuristics in v1. Prefer under-promising worker capacity over over-enrolling weak nodes.

## K. Observability and operator visibility

### Question
What minimum logs and metrics are required to debug the network during v1?

### Why it matters

A trust router cannot improve if failures are opaque.

### Decisions needed

- What request lifecycle events must be logged?
- Which worker/model health metrics must be queryable by operators?
- What local logs should the worker bridge expose to contributors?
- What should the smoke test record for diagnosis?

### Recommended initial answer

Instrument request receipt, assignment, claim, completion, timeout, retry, and normalization failure from the start.

## L. Future degradation policy shape

### Question
How should future graceful degradation be represented so it can be added cleanly later?

### Why it matters

Even if deferred, the routing contracts should not paint the platform into a corner.

### Decisions needed

- Will fallback policy live in user settings, request metadata, or model configuration?
- How will "trusted equivalent" models eventually be defined?
- What user language maps to `strict`, `balanced`, and `economy` behavior?

### Recommended initial answer

Do not implement degradation yet, but reserve a clear place in request policy and model metadata for later fallback rules.

## Decision priority

If we want to start building quickly, these should be resolved first:

1. supported model policy
2. model identity rules
3. streaming scope
4. trusted fallback requirement
5. client implementation shape
6. authentication and tenant isolation

---

# 13. Recommended implementation order

## Phase 0: prove transport
- one hardcoded worker
- one hardcoded model
- Modulo implements `POST /api/chat`
- OpenClaw can talk through Modulo and get a remote response

## Phase 1: minimal real router
- worker register/heartbeat/claim/result
- multiple workers
- model-to-worker lookup
- simple healthy/loaded routing

## Phase 2: local client magic
- Modulo client can connect OpenClaw automatically
- Modulo client can enable worker automatically
- smoke test integrated

## Phase 3: reliability
- timeouts
- retries
- health scoring
- basic worker confidence
- buyer-to-worker continuity via short-lived leases when it improves warm-path UX

Do not move beyond phase 3 until onboarding is rock solid.

## Phase 4+: trust router evolution

Only after the core path is solid:

- introduce curated `Cloud` execution path
- make execution mode user-visible
- add policy-aware fallback
- add curated model equivalence classes
- tune routing by trust, cost, and latency

---

# 14. Definition of done for v1

Modulo v1 is done when all of these are true:

1. A user can install Modulo without editing any config files.
2. A user can click Connect OpenClaw and have OpenClaw use a selected Modulo network model.
3. A remote worker can host that selected model through local Ollama.
4. OpenClaw can send a request to Modulo and receive a valid response from the remote worker.
5. Worker failures do not silently break the request path.
6. A user can explicitly enable hosting and contribute a local supported model.

## The one demo that proves v1

1. Laptop installs Modulo.
2. User clicks Connect OpenClaw.
3. User selects `llama3.1:8b`.
4. OpenClaw sends a message.
5. Modulo routes the request to a worker machine thousands of miles away.
6. Response comes back successfully.
7. Worker bridge logs a completed job.

If that works reliably, onboarding is won.

---

# 15. Build guidance for Codex

## Architectural guardrails

- keep everything literal and named-model based
- do not add capability abstraction
- do not add marketplace mechanics yet
- do not add hidden background mutations to OpenClaw or worker state
- keep worker bridge pull-based
- keep Modulo cloud API Ollama-compatible first
- treat response normalization as a hard requirement
- design the router so `Local`, `Network`, and `Cloud` can share one policy framework later
- keep fallback explicit and policy-driven rather than implicit and magical
- treat exact model identity as a trust concern, not just a metadata field
- choose slices that strengthen the roadmap-critical demo path instead of widening surface area
- keep `client` thin and supervisory while `worker` owns execution behavior
- prefer continuity-preserving router behavior over stateless request thrash when it materially improves UX

## Primary engineering objective

**Make OpenClaw think Modulo is just a remote Ollama host, while Modulo quietly routes work to distributed workers.**

## Product objective

**One click to connect OpenClaw. One click to enable hosting. No hand edits.**

## Strategic objective

**Build the trust-weighted router that can eventually make `Network` the default low-cost path, with `Cloud` as the curated fallback and `Local` as the privacy anchor.**
