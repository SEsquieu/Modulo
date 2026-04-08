# Modulo

Initial scaffold for the Modulo v1 platform.

This repo currently codifies the recommended v1 decisions from the design doc:

- curated supported model list
- exact model-name matching in v1
- separate execution modes: `local`, `network`, `cloud`
- network routing based on trust and health
- exact-model trusted cloud fallback only
- no model substitution in v1

## Layout

- `src/modulo/common`: shared types, catalog, and v1 policy defaults
- `src/modulo/service`: in-memory routing and service layer
- `tests`: unit tests for the v1 routing behavior

## Running tests

```powershell
python -m unittest discover -s tests
```

