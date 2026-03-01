# FinOps Kubernetes Operator

This repository contains a lightweight Kubernetes operator that scales
Deployments and StatefulSets down to zero during scheduled "sleep" windows
for cost-saving (FinOps) purposes. The operator is written in Python using
[Kopf](https://kopf.readthedocs.io/).

## Components

- `operator.py` - main operator logic
- `Dockerfile` - builds the container image
- `chart/finops-operator` - Helm chart for installing the operator

## Building and Publishing the Image

```bash
# build locally
docker build -t ghcr.io/<your-org>/finops-operator:0.1.0 .

# push to GitHub Container Registry (replace <org> and make sure you are logged in):
# echo $CR_PAT | docker login ghcr.io -u <username> --password-stdin
docker push ghcr.io/<your-org>/finops-operator:0.1.0
```

You can set `image.repository` and `image.tag` values when installing the
Helm chart (see below).

## Installing with Helm

```bash
# add your chart repo or install from local directory
helm install finops-operator ./chart/finops-operator \
  --set image.repository=ghcr.io/<org>/finops-operator \
  --set image.tag=0.1.0
```

The chart creates a ServiceAccount, ClusterRole, ClusterRoleBinding, and
Deployment. RBAC rules are limited to reading namespaces, listing pods, and
patching deployments/statefulsets.

## Configuration

Customize via `values.yaml` or `--set` flags:

| Value                      | Description                         | Default                  |
|---------------------------|-------------------------------------|--------------------------|
| `image.repository`        | Container image to run              | `ghcr.io/my-org/finops-operator` |
| `image.tag`               | Image tag                           | `latest`                 |
| `image.pullPolicy`        | Image pull policy                   | `IfNotPresent`           |
| `serviceAccount.create`   | Whether to create a SA              | `true`                   |
| `rbac.create`             | Create RBAC resources               | `true`                   |
| `annotations`             | Annotations on SA/deployment        | `{}`                     |
| `scheduleInterval`        | Kopf timer interval (seconds)       | `60`                     |

## Development

Run the operator locally with your kubeconfig:

```bash
pip install -r requirements.txt
kopf run operator.py --verbose
```

Or build-and-push the image and install the chart as above.

## Testing

See `tests/` for unit and integration examples (coming soon).

## Publishing the Helm Chart

You can package and publish the chart to GitHub Pages or an OCI registry:

```bash
# package locally
helm package chart/finops-operator

# to an OCI registry (e.g. GitHub Packages):
helm registry login ghcr.io
helm push chart/finops-operator-0.1.0.tgz oci://ghcr.io/<org>/helm-charts
```
