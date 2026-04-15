---
name: colima
description: 'Set up, manage, and troubleshoot Colima container runtimes on macOS and Linux. Use for Docker/Containerd/Incus VM lifecycle, Kubernetes clusters, GPU-accelerated AI workloads, and container runtime configuration.'
argument-hint: 'Runtime type, VM resources, and operational goal'
user-invocable: true
---

# Colima

## When to Use
- Starting, stopping, or configuring Colima container VMs.
- Running Docker, Containerd, Incus, or Kubernetes via Colima.
- Customizing VM resources (CPU, memory, disk, VM type).
- Setting up GPU-accelerated AI model workloads with krunkit.
- Troubleshooting container runtime connectivity or performance.
- Using Colima as a Docker Desktop alternative.

## Reference
- Docs: https://colima.run/docs/
- Source: https://github.com/abiosoft/colima
- FAQ: https://github.com/abiosoft/colima/blob/main/docs/FAQ.md

## Installation
```bash
# Homebrew (recommended)
brew install colima

# MacPorts
sudo port install colima

# Nix
nix-env -iA nixpkgs.colima
```

Docker client is required for Docker runtime: `brew install docker`.
kubectl is required for Kubernetes: `brew install kubectl`.

## Procedure
1. Install Colima and the client for the target runtime (Docker, nerdctl, incus, kubectl).
2. Start the VM with the desired runtime and resource profile.
3. Verify the runtime is working (`docker ps`, `nerdctl ps`, `incus list`, or `kubectl get pods`).
4. Customize VM resources or runtime configuration as needed.
5. Ensure the Docker socket is available and referenced correctly by dependent tools.

## Runtimes Quick Reference

### Docker (default)
```bash
colima start
docker run hello-world
docker ps
```

### Containerd
```bash
colima start --runtime containerd
colima nerdctl install          # install nerdctl alias
nerdctl run hello-world
```

### Kubernetes
```bash
colima start --kubernetes
kubectl run caddy --image=caddy
kubectl get pods
```

### Incus (containers and VMs)
```bash
colima start --runtime incus
incus launch images:alpine/edge
incus list
```

### AI Models (GPU accelerated, Apple Silicon, macOS 13+)
```bash
brew tap slp/krunkit && brew install krunkit
colima start --runtime docker --vm-type krunkit
colima model run gemma3
```

## VM Customization
```bash
# Create VM with specific resources
colima start --cpu 4 --memory 8 --disk 50

# Modify existing VM (stop first)
colima stop
colima start --cpu 8 --memory 16

# Rosetta 2 emulation (Apple Silicon, macOS >= 13)
colima start --vm-type=vz --vz-rosetta

# Edit config file interactively
colima start --edit
```

## Multiple Instances
```bash
# Start a named instance
colima start --profile dev
colima start --profile ci --cpu 2 --memory 4

# List instances
colima list

# Stop a specific instance
colima stop --profile dev
```

## Docker Socket Integration
When using Colima as the Docker runtime for containerized projects:
```bash
# Start Colima with enough resources
colima start --cpu 4 --memory 4 --disk 20

# Verify Docker socket is available
docker context ls
```

If Docker Compose or other tools cannot find the Docker socket, set:
```bash
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
```

## Troubleshooting
- **VM won't start**: check `colima status`, try `colima delete` and recreate.
- **Docker socket not found**: verify `docker context ls` and set `DOCKER_HOST` if needed.
- **OOM or slow builds**: increase memory with `colima stop && colima start --memory 8`.
- **Port forwarding issues**: Colima auto-forwards ports; check `colima list` for VM status.
- **Rosetta errors**: ensure macOS >= 13 (Ventura) on Apple Silicon and use `--vm-type=vz`.

## Review Checklist
- Runtime and VM type match the workload requirements.
- CPU, memory, and disk are sized appropriately for the task.
- Docker client or relevant runtime CLI is installed.
- Docker socket path is correctly configured for dependent tools (OpenClaw, docker-compose).
- Named profiles are used when multiple instances are needed.
