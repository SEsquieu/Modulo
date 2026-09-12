# Public release checklist

Use this list before changing the repository visibility or creating `v0.1.0-alpha`.

## Completed in the release-prep pass

- [x] Rewrite the README around the implemented distributed inference fabric
- [x] Distinguish Modulo from Ollama
- [x] Distinguish centrally coordinated routing from a pure peer-to-peer mesh
- [x] Add an architecture diagram and package responsibility map
- [x] Document implemented behavior separately from reserved/future scopes
- [x] Add an explicit trusted-environment security warning
- [x] Add Apache-2.0 license
- [x] Add contributing, security, changelog, routing, status, and quick-start docs
- [x] Add package metadata and command entry points
- [x] Add a Windows GitHub Actions test workflow
- [x] Expand ignore rules for environment files, credentials, keys, and local Modulo state
- [x] Remove machine-specific absolute documentation links
- [x] Scan the current tree for credential-shaped content
- [x] Scan all 159 reachable commits (711 unique historical blobs) for common credential signatures and risky credential filenames
- [x] Verify editable installation and Python compilation
- [x] Isolate and fix intermittent onboarding health reporting after a failed smoke test

## Must verify on the supported target

- [ ] Push the release-prep branch and confirm the Windows CI job passes all 132 tests
- [ ] Follow [quickstart.md](./quickstart.md) from a clean clone on machine A
- [ ] Follow it from a clean clone on machine B
- [ ] Prove the stub request, inspect the route trace, then prove real Ollama execution
- [ ] Confirm stopping the worker removes its advertised capacity
- [ ] Confirm the README renders correctly on GitHub, including Mermaid

## GitHub release settings

- [ ] Set the repository description to: `Distributed inference fabric for routing LLM workloads across local and private-network compute.`
- [ ] Add topics: `llm`, `inference`, `ollama`, `distributed-systems`, `model-routing`, `local-ai`
- [ ] Enable Issues
- [ ] Enable private vulnerability reporting
- [ ] Confirm the default branch is `main`
- [ ] Confirm no branch or environment settings expose credentials
- [ ] Make the repository public only after the clean-clone proof and green CI
- [ ] Create tag and GitHub prerelease `v0.1.0-alpha`

## Suggested release note

Modulo `v0.1.0-alpha` is the first public engineering release of an experimental distributed inference fabric. It demonstrates scope-aware and capacity-aware routing, worker lifecycle and job transport, Ollama execution, streaming, route traces, continuity leases, and compatible consumer ingress across trusted local/private machines.

This release is intended for inspection, experimentation, and trusted-network testing. It is not authenticated, Internet-hardened, or production-ready.

