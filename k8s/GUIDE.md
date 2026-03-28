# Relic k3d Deployment Guide

Multi-environment Kubernetes deployment using k3d. One cluster hosts multiple isolated environments (testing, dev, demo, PR previews), each with its own Cloudflare tunnel and subdomain.

## Architecture

```
Host machine (Fedora)
└── k3d cluster "relic"
    ├── namespace: shared
    │   ├── postgres        (one instance, multiple databases)
    │   └── minio           (one instance, multiple buckets)
    ├── namespace: runners
    │   └── github-runner   (self-hosted Actions runner)
    ├── namespace: relic-testing
    │   ├── backend + frontend + cloudflared
    │   └── tunnel: tunnel-testing → testing.your.domain
    ├── namespace: relic-demo-acme
    │   ├── backend + frontend + cloudflared
    │   └── tunnel: tunnel-demo-acme → demo-acme.your.domain
    └── namespace: relic-pr-42
        ├── backend + frontend + cloudflared
        └── tunnel: tunnel-pr-42 → pr-42.your.domain
```

Each environment gets:
- Isolated k8s namespace
- Dedicated PostgreSQL database
- Dedicated MinIO bucket
- Dedicated Cloudflare tunnel with its own subdomain

---

## Prerequisites

### Install on Fedora

```bash
# Docker
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker

# kubectl
sudo tee /etc/yum.repos.d/kubernetes.repo <<EOF
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/repodata/repomd.xml.key
EOF
sudo dnf install -y kubectl

# k3d
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# jq
sudo dnf install -y jq
```

### Install on Ubuntu

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# kubectl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update && sudo apt-get install -y kubectl

# k3d
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# jq
sudo apt-get install -y jq
```

Log out and back in after `usermod` for Docker group to take effect.

---

## One-Time Setup

### 1. Cloudflare credentials

You need three values from Cloudflare:

| Value | Where to find it |
|---|---|
| `CLOUDFLARE_API_TOKEN` | My Profile → API Tokens → Create Token. Use "Edit Cloudflare Workers" template, add **Cloudflare Tunnel: Edit** and **DNS: Edit** permissions. |
| `CLOUDFLARE_ACCOUNT_ID` | Any domain page → right sidebar → Account ID |
| `CLOUDFLARE_ZONE_ID` | Your domain page → right sidebar → Zone ID |

### 2. GitHub token

Create a **classic PAT** (not fine-grained, not a runner registration token):

GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate → check **`repo`** scope.

### 3. Bootstrap the cluster

```bash
make k8s-bootstrap \
  K8S_DOMAIN=your.domain.com \
  CLOUDFLARE_API_TOKEN=your_cf_token \
  CLOUDFLARE_ACCOUNT_ID=your_account_id \
  CLOUDFLARE_ZONE_ID=your_zone_id \
  GITHUB_RUNNER_TOKEN=ghp_your_github_pat
```

This is idempotent — safe to run again. It:
- Creates the k3d cluster
- Deploys shared PostgreSQL and MinIO
- Creates the GitHub Actions self-hosted runner
- Stores all credentials in `k8s/.cluster-secrets.env` (gitignored)

After bootstrap, verify everything is running:

```bash
make k8s-status
```

---

## Environments

### Static environments (testing, dev, demo)

These have checked-in overlay configs in `k8s/overlays/`. They persist across deploys and keep their data on teardown by default.

```bash
# Deploy / update
make k8s-deploy K8S_ENV=testing
make k8s-deploy K8S_ENV=testing K8S_VERSION=v1.2.3   # specific image tag

# Remove namespace (keeps database + bucket)
make k8s-teardown K8S_ENV=testing

# Remove namespace + destroy all data
make k8s-teardown-clean K8S_ENV=testing
```

First deploy of a static env creates:
- Cloudflare tunnel `tunnel-testing`
- DNS record `testing.your.domain.com`
- Database `relic_testing` + user
- MinIO bucket `relic-testing`
- Credentials stored in `k8s/overlays/testing/secrets/` (gitignored)

### Dynamic demo environments

Named freely, provisioned on demand, seeded with demo data. Created in `k8s/overlays/<name>/` at runtime (gitignored).

```bash
# Create with auto-generated name (e.g. relic-demo-a3f9bx)
make k8s-demo

# Create with specific name
make k8s-demo K8S_ENV=demo-acme

# Create with specific version
make k8s-demo K8S_ENV=demo-acme K8S_VERSION=v1.2.3

# List all running demos
make k8s-list-demos

# Tear down one demo (always destroys data)
make k8s-teardown-clean K8S_ENV=demo-acme

# Tear down ALL demos at once
make k8s-teardown-all-demos
```

### Re-seeding

```bash
make k8s-seed K8S_ENV=demo-acme K8S_SEED=demo
```

---

## Day-to-day Operations

```bash
# Stream backend logs
make k8s-logs K8S_ENV=testing

# Open shell in backend pod
make k8s-shell K8S_ENV=testing

# Run integration tests against an environment
make k8s-test K8S_ENV=testing

# Show all environments and pod status
make k8s-status
```

---

## GitHub Actions CI

The self-hosted runner in the cluster handles deploy jobs. Two secrets and one variable must be set in GitHub (repo Settings → Secrets and variables → Actions):

**Variables:**
- `K8S_DOMAIN` — your base domain (e.g. `your.domain.com`)

**Secrets:**
- `RELIC_ADMIN_CLIENT_IDS` — admin client ID(s) for the deployed app
- `CLOUDFLARE_API_TOKEN` — same token used in bootstrap
- `CLOUDFLARE_ACCOUNT_ID` — same account ID
- `CLOUDFLARE_ZONE_ID` — same zone ID

### PR preview environments

Opening a PR automatically:
1. Builds images tagged `pr-<number>` (runs on GitHub-hosted `ubuntu-latest`)
2. Deploys `relic-pr-<number>` namespace on the self-hosted runner
3. Runs integration tests
4. Posts a comment with the URL

Closing/merging the PR:
1. Tears down the namespace
2. Drops the database and bucket
3. Deletes the Cloudflare tunnel and DNS record

---

## Cluster Management

```bash
# Delete the entire cluster (IRREVERSIBLE — all data lost)
make k8s-cluster-delete

# Re-bootstrap from scratch (after cluster-delete)
make k8s-bootstrap K8S_DOMAIN=... CLOUDFLARE_API_TOKEN=... ...
```

Credentials are preserved in `k8s/.cluster-secrets.env` across cluster deletes, so re-bootstrapping reuses the same passwords.

---

## Troubleshooting

### cloudflared pod in CrashLoopBackOff

```bash
kubectl logs -n relic-<env> deployment/cloudflared
```

Common causes:
- **"requires ID or name"** — token not being injected. Check the `cloudflared-token` Secret exists in the namespace: `kubectl get secret cloudflared-token -n relic-<env>`
- **"cert.pem not found"** — `tunnel:` field is present in the config. It must not be there when using `--token`.
- **Killed after ~30s** — liveness probe failing (only affects multiple pods on same node). Probe is disabled in current config.

### Backend not starting

```bash
kubectl logs -n relic-<env> deployment/backend -c migrate   # init container
kubectl logs -n relic-<env> deployment/backend              # main container
```

The init container runs database migrations before the backend starts. If it fails, check the DATABASE_URL secret is correct.

### GitHub runner not registering

```bash
kubectl logs -n runners -l app=github-runner
```

- **"Invalid configuration provided for token"** — the stored token is a runner registration token (expires after 1 hour) instead of a classic PAT. Recreate the secret with a PAT (`ghp_...` with `repo` scope):
  ```bash
  kubectl create secret generic runner-secret \
    --namespace runners \
    --from-literal="GITHUB_TOKEN=ghp_your_pat" \
    --dry-run=client -o yaml | kubectl apply -f -
  kubectl rollout restart deployment/github-runner -n runners
  ```

### Credential updates

To update Cloudflare credentials after bootstrap:

```bash
# Edit the secrets file directly
nano k8s/.cluster-secrets.env

# Or re-run bootstrap (idempotent, rewrites the file)
make k8s-bootstrap CLOUDFLARE_API_TOKEN=new_token K8S_DOMAIN=your.domain.com ...
```

---

## File Reference

```
k8s/
├── .cluster-secrets.env          # GITIGNORED — passwords + CF credentials
├── k3d-config.yaml               # Cluster definition
├── base/                         # Kustomize base (all envs inherit this)
│   ├── backend/
│   ├── frontend/
│   └── cloudflared/
├── overlays/
│   ├── testing/                  # Static env (checked in)
│   ├── dev/                      # Static env (checked in)
│   ├── demo/                     # Static env (checked in)
│   └── demo-*/                   # GITIGNORED — generated at runtime
├── shared/
│   ├── postgres/                 # PostgreSQL StatefulSet + Service
│   └── minio/                    # MinIO StatefulSet + Service
├── runners/
│   └── deployment.yaml           # GitHub Actions self-hosted runner
├── seeds/
│   ├── demo.sh                   # Demo seed data
│   └── testing.sh                # Testing fixtures
└── scripts/
    ├── bootstrap.sh              # One-time cluster setup
    ├── provision-env.sh          # Create/update an environment
    ├── teardown-env.sh           # Remove an environment
    └── lib/
        ├── cloudflare.sh         # Cloudflare REST API helpers
        ├── colors.sh             # Terminal output helpers
        └── wait-for.sh           # kubectl wait wrappers
```
