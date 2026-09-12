# Project status

Modulo is an experimental distributed inference fabric and a working systems prototype. It is not a production service.

## Release boundary

The `0.1.0-alpha` release is intended to make the architecture, implementation, and demonstrated private-network path inspectable and reproducible.

### Implemented

- in-process and URL-backed worker transports
- worker registration, heartbeat, job claim, completion, failure, and unregister lifecycle
- Ollama-backed and stub execution adapters
- exact-model routing by worker kind and scope
- private-network membership filtering
- worker health and concurrency filtering
- trust/runtime scoring from confidence, recent success rate, timeout rate, and headroom
- job retry and worker exclusion paths
- buffered and streamed result transport
- route-trace lifecycle and filtered-worker reasons
- short-lived buyer/model continuity leases
- Ollama-shaped and OpenAI-compatible ingress
- desktop engineering control surface
- Continue configuration backup, managed block, metadata, and rollback

### Demonstrated

- one-process end-to-end execution through real package boundaries
- private-scope execution between separate machines
- execution between machines on separate physical networks through an external tunnel
- real Ollama-backed response streaming
- Continue requests through the OpenAI-compatible ingress

### Reserved or incomplete

- `Public` and `Cloud` are represented in contracts and UI vocabulary, but are not a production capacity marketplace or managed provider service
- control-plane state is in memory
- security hardening is incomplete
- the GUI is a proving surface rather than a packaged tray product
- host capability benchmarking and dynamic model swapping remain design work
- protocol/version compatibility is not yet stable

## What the alpha proves

The alpha proves that inference can be treated as a routed distributed workload while preserving explicit runtime boundaries:

1. a consumer submits a model-specific request;
2. the control plane evaluates eligible capacity;
3. a worker claims the job;
4. an executor runs the requested model;
5. the result or stream crosses back through the control plane;
6. trace state explains the route and outcome.

It does not prove safe multi-tenant operation, arbitrary Internet exposure, or production reliability.

