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
- `src/modulo/service`: in-memory routing, worker/job control plane, and HTTP transport
- `tests`: unit tests for the v1 routing behavior

## Running the demo server

```powershell
python -m pip install -e .
python -m modulo.service.demo_server
```

Then try:

```powershell
curl http://127.0.0.1:8000/api/tags
curl -Method Post http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"model":"llama3.1:8b","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

## Worker protocol endpoints

The current scaffold includes these worker-facing HTTP routes:

- `POST /worker/register`
- `POST /worker/heartbeat`
- `POST /worker/jobs/claim`
- `POST /worker/jobs/{job_id}/result`
- `POST /worker/jobs/{job_id}/fail`

They currently use simple JSON payloads and map directly onto the in-memory control plane.

## Running tests

```powershell
python -m unittest discover -s tests
```
