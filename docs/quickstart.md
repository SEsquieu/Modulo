# Quick start

This guide proves the distributed path before involving a real model, then swaps in Ollama.

## Requirements

- two Windows machines on a trusted LAN or private VPN
- Python 3.11 or newer on both machines
- TCP port 8000 reachable from the worker to the control-plane machine
- Ollama and an installed model only for the real-execution step

Do not expose the alpha server directly to the public Internet.

## 1. Install on both machines

```powershell
git clone https://github.com/SEsquieu/Modulo.git
cd Modulo
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## 2. Start the control plane

On machine A:

```powershell
python -m modulo.cloud.server --host 0.0.0.0 --port 8000
```

Allow inbound TCP 8000 only from the trusted network you are using. Record machine A's reachable private IP address.

## 3. Start a stub worker

On machine B:

```powershell
python -m modulo.worker.bridge_runner `
  --modulo-url http://MACHINE_A_IP:8000 `
  --worker-id worker-b `
  --model gemma4:e2b `
  --scope private `
  --private-network-id home-lab `
  --stub-response "response executed on machine B"
```

The stub validates registration, routing, job claim, and result transport without downloading or loading a model.

## 4. Send a private-scope request

On machine A or another trusted machine:

```powershell
$body = @{
  model = "gemma4:e2b"
  messages = @(@{ role = "user"; content = "Reply briefly." })
  stream = $false
  scope = "private"
  private_network_id = "home-lab"
  buyer_id = "quickstart"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri http://MACHINE_A_IP:8000/api/chat `
  -ContentType "application/json" `
  -Body $body
```

Expected response content includes `response executed on machine B`.

If routing fails, check:

- the worker is still running;
- both commands use the same model ID;
- request and worker use the same `private_network_id`;
- machine B can reach `http://MACHINE_A_IP:8000/api/platform/status`;
- the worker did not report an error.

## 5. Inspect route truth

```powershell
Invoke-RestMethod http://MACHINE_A_IP:8000/api/platform/trace/latest |
  ConvertTo-Json -Depth 8
```

The trace should identify `worker-b`, the resolved private scope, the route reason, and the final job status.

## 6. Switch to real Ollama execution

Stop the stub worker with Ctrl+C. On machine B, verify Ollama and the desired model:

```powershell
ollama list
ollama run gemma4:e2b "Reply with READY"
```

Start the bridge again without `--stub-response`:

```powershell
python -m modulo.worker.bridge_runner `
  --modulo-url http://MACHINE_A_IP:8000 `
  --worker-id worker-b `
  --model gemma4:e2b `
  --scope private `
  --private-network-id home-lab
```

Repeat the request from step 4. The response now comes from Ollama on machine B.

## Local one-process proof

For a quick package-level smoke test on one machine:

```powershell
python -m modulo.prototype
```

This is useful for verifying installation, but it does not replace the two-machine proof.
