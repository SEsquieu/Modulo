# Contributing

Modulo is an early engineering alpha. Focused issues and pull requests are welcome.

## Before opening a change

1. Read [the architecture guide](./docs/architecture.md).
2. Keep responsibility in the correct package:
   - `client` supervises and configures;
   - `worker` executes and reports facts;
   - `cloud` routes and coordinates;
   - `common` defines shared contracts and policy.
3. Do not present reserved `Public` or `Cloud` behavior as production-ready.
4. Preserve exact-model and scope boundaries unless the change explicitly revises policy.
5. Add or update tests for behavior changes.

## Development setup

The current tested target is Windows with Python 3.11 or newer.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[gui]"
python -m unittest discover -s tests -v
```

Ollama is not required for the unit suite. Use the stub executor in [the quick start](./docs/quickstart.md) when validating transport without a local model.

## Pull requests

Keep pull requests narrow and describe:

- the user or operator problem
- the runtime boundary affected
- the behavior before and after
- how the change was tested
- any security or compatibility implications

Do not include credentials, machine-specific state, generated build artifacts, or unrelated formatting changes.

