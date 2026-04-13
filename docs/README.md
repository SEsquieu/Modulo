# Docs

Project documentation lives here as the repo grows.

Current source of truth:

- [handoff.md](./handoff.md): quick resume file for workstation handoff and current implementation context
- [../modulo_v_1_design_doc.md](../modulo_v_1_design_doc.md): product and architecture direction for Modulo v1
- [roadmap.md](./roadmap.md): current development phase, completed slices, and upcoming roadmap-aligned slices
- [gui_roadmap.md](./gui_roadmap.md): GUI-client-specific build plan, phased slices, and UI guardrails
- [gui_state_map.md](./gui_state_map.md): first GUI screens, view-model mapping, and command/event inventory
- [phase_2_plan.md](./phase_2_plan.md): sequenced next-phase integration plan after the initial backend and GUI roadmaps
- [ollama_discovery_roadmap.md](./ollama_discovery_roadmap.md): mini roadmap for truthful local Ollama discovery
- [hosting_readiness_roadmap.md](./hosting_readiness_roadmap.md): mini roadmap for real hosting preflight and readiness
- [session_bridge_roadmap.md](./session_bridge_roadmap.md): mini roadmap for the always-on client control-plane/session bridge
- [openclaw_integration_roadmap.md](./openclaw_integration_roadmap.md): mini roadmap for real OpenClaw detection and connection flow
- [real_execution_roadmap.md](./real_execution_roadmap.md): mini roadmap for real Ollama-backed execution
- [host_warm_state_roadmap.md](./host_warm_state_roadmap.md): mini roadmap for host-side warm-state visibility and prewarm lifecycle
- [productization_checklist.md](./productization_checklist.md): compact gated checklist for packaging and trust polish
- [private_networks_design.md](./private_networks_design.md): architectural note for access-controlled private Modulo networks inside an org boundary
- [platform_layering_spec.md](./platform_layering_spec.md): canonical product-shape doc for tray-first layering, progressive disclosure, and what belongs in each UI/system layer
- [private_scope_mvp_design.md](./private_scope_mvp_design.md): implementation-narrowing doc for treating the first bounded remote-execution proof as `Private` scope
- [private_mvp_roadmap.md](./private_mvp_roadmap.md): mini roadmap for the first private-scope remote execution proof
- [route_trace_visibility_roadmap.md](./route_trace_visibility_roadmap.md): mini roadmap for surfacing routed execution truth after the private proof is real
- [use_side_truth_roadmap.md](./use_side_truth_roadmap.md): mini roadmap for making the `Use` side truthful about `Local / Private / Public / Cloud` visibility and routing
- [continue_consumer_roadmap.md](./continue_consumer_roadmap.md): mini roadmap for making `Continue (VSCode)` the first non-OpenClaw mounted consumer through the `OpenAI API` shape

Current emphasis:

- the cross-network private execution proof is now real
- route-trace visibility is now completed
- the `Use`-side truth roadmap is now completed
- the Continue consumer roadmap is now the newest focused consumer-integration roadmap
- the Continue consumer roadmap is now completed through Slice 2, so the next concrete step is real apply/rollback against the scoped Continue ownership contract
- productization is intentionally deferred while shared-path truth, second-layer GUI refinement, and policy harden
- the current UI should be treated as a second-layer surface while the product continues to aim toward a tray-first release
- the current live GUI cleanup is focused on:
  - calmer `Use` and `Mount` semantics
  - a more trustworthy `Active Route` summary
  - a nested anchored `Use` model picker that respects `Local / Private / Public / Cloud` and real scope names

Recommended next docs to add:

- `api.md`: Ollama-facing and worker-facing HTTP contracts
- `onboarding.md`: use-side and host-side flows from the tray client
- `operations.md`: health, logging, and deployment expectations
