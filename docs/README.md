# Documentation

The public documentation path is intentionally short:

1. [Quick start](./quickstart.md) — prove two-machine routing with a stub, then use Ollama.
2. [Architecture](./architecture.md) — understand runtime ownership and system boundaries.
3. [Routing](./routing.md) — inspect eligibility, scoring, continuity, fallback, and traces.
4. [Project status](./project-status.md) — separate implemented proof from reserved or incomplete work.
5. [Security](../SECURITY.md) — understand the current trust boundary before exposing a service.
6. [Public release checklist](./release-checklist.md) — finish the clean-clone, CI, and GitHub publication gates.

## Active engineering references

- [Platform layering](./platform_layering_spec.md)
- [Private-scope design](./private_scope_mvp_design.md)
- [Private-network design](./private_networks_design.md)
- [Productization checklist](./productization_checklist.md)

## Development history and design archive

The remaining documents preserve the implementation sequence and product reasoning. They are useful context, but they are not all descriptions of current behavior.

Historical roadmaps may contain older terminology such as a singular `network` pool, pre-streaming assumptions, or placeholder implementation state. When a historical document conflicts with the README, architecture guide, routing guide, project-status page, or code, prefer those current sources.

- [Main roadmap](./roadmap.md)
- [Phase 2 plan](./phase_2_plan.md)
- [GUI roadmap](./gui_roadmap.md)
- [GUI state map](./gui_state_map.md)
- [Client local-state roadmap](./client_local_state_roadmap.md)
- [Continue consumer roadmap](./continue_consumer_roadmap.md)
- [Host warm-state roadmap](./host_warm_state_roadmap.md)
- [Hosting readiness roadmap](./hosting_readiness_roadmap.md)
- [Ollama discovery roadmap](./ollama_discovery_roadmap.md)
- [OpenClaw integration roadmap](./openclaw_integration_roadmap.md)
- [Private MVP roadmap](./private_mvp_roadmap.md)
- [Real-execution roadmap](./real_execution_roadmap.md)
- [Route-trace visibility roadmap](./route_trace_visibility_roadmap.md)
- [Session-bridge roadmap](./session_bridge_roadmap.md)
- [Use-side truth roadmap](./use_side_truth_roadmap.md)
- [Future host-capacity intelligence](./future_host_capacity_intelligence.md)
- [Workstation handoff notes](./handoff.md)
- [Original v1 design document](../modulo_v_1_design_doc.md)
