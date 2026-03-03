# FinOps Kubernetes Operator

This repository contains a lightweight Kubernetes operator that scales
Deployments and StatefulSets down to zero during scheduled "sleep" windows
for cost-saving (FinOps) purposes. The operator is written in Python using
[Kopf](https://kopf.readthedocs.io/).

## Components

- `operator.py` - main operator logic
- `Dockerfile` - builds the container image
- `helm-chart/finops-k8s-operator` - Helm chart for installing the operator

## Building and Publishing the Image

docker build -t ghcr.io/<your-org>/finops-operator:0.1.0 .
docker push ghcr.io/<your-org>/finops-operator:0.1.0
```bash
# build locally (replace <version> with whatever tag you intend)
docker build -t ghcr.io/<your-org>/finops-operator:<version> .

# push to GitHub Container Registry (replace <org> and make sure you are logged in):
# echo $CR_PAT | docker login ghcr.io -u <username> --password-stdin
docker push ghcr.io/<your-org>/finops-operator:<version>
```

You can set `image.repository` and `image.tag` values when installing the
Helm chart (see below).

## Installing with Helm

### Annotate the namespace schedule

Before the operator can do anything you need to tell it when to sleep.  Add
an annotation with your desired window (UTC) on the namespace:

```sh
kubectl annotate ns projectabc finops-operator/sleep-schedule="18:00-07:00"
```

The controller only runs its timer for namespaces that carry that annotation
(in addition to the usual 60‑second interval).  It also ignores any namespace
whose name begins with `kube-` and a handful of other control‑plane
namespaces, so even though the ClusterRole is cluster‑wide, the operator
never actively touches the system namespaces.  This behaviour is implemented
in the Python code and is noted here for security reviewers.

> **RBAC note:** Kopf internally patches the namespace to record its last
> invocation, so the operator requires `patch` permission on the
> `namespaces` resource.  The supplied Helm chart now grants `get,list,watch,
> patch` for namespaces; if you install the chart manually, make sure the
> ClusterRole/Role has the same verbs.  Namespace filtering is handled in the
> code; it’s not possible to express an “exclude kube-*” condition in the
> ClusterRoleBinding itself.

You can update the schedule at any time and the timer will pick it up on the
next interval.

### Opting workloads into scaling

The operator doesn’t touch every resource in a namespace – you **must** mark
Deployments and StatefulSets you want to control.  Either a **label** or an
**annotation** with the key `finops-operator/scalable` set to `"true"` will
work, e.g.:

```sh
kubectl label deploy my-app finops-operator/scalable=true
# or equivalently:
kubectl annotate deploy my-app finops-operator/scalable=true
```

Since the operator checks both `metadata.labels` and `metadata.annotations`,
feel free to use whichever fits your workflow.


```bash
# install from local chart directory (replace <version> as needed)
helm install finops-operator ./helm-chart/finops-k8s-operator \
  --set image.repository=ghcr.io/<org>/finops-operator \
  --set image.tag=<version>
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
```bash
# package locally (will create finops-k8s-operator-<chart-version>.tgz)
helm package helm-chart/finops-k8s-operator

# to an OCI registry (e.g. GitHub Packages):
helm registry login ghcr.io
# replace <chart-version> with the version you just packaged
helm push finops-k8s-operator-<chart-version>.tgz oci://ghcr.io/<org>/helm-charts
```

The GitHub Actions workflow included in this repository will take care of
building the container image and also packaging/pushing the Helm chart when
you push a tag (e.g. `v0.1.0`). The chart is stored alongside the images in
the registry under the `helm-charts` path; you can view it in the **Packages**
tab of your repo or pull it directly:

```bash
helm registry login ghcr.io
helm pull oci://ghcr.io/<org>/helm-charts/finops-operator --version <chart-version>

The workflow also automatically bumps `Chart.yaml` to match the tag and
commits that change back to `main` so the repository file stays in sync.
```

To pull the operator image manually, run:

```bash
docker pull ghcr.io/ok-karthik/finops-k8s-operator:latest
``` (or replace `latest` with a specific tag)

And if you prefer to install the chart from the registry instead of a local
directory:

```bash
helm registry login ghcr.io
helm install finops-operator oci://ghcr.io/<org>/helm-charts/finops-operator --version <chart-version>
```
