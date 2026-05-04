# Kube Up Helm Chart

Official Helm chart for deploying Kube Up, a Kubernetes operator for running synthetic checks using Kubernetes CronJobs. It defines the `KubeUpCheck` [CRD](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) for check configuration and the `KubeUpState` CRD for status tracking.

## Components

This chart deploys:

- CRDs
  - `KubeUpCheck`
  - `KubeUpState`
- Kube Up Manager - Operator that watches `KubeUpCheck` resources and manages corresponding `CronJob`s
- Kube Up API - REST API for receiving check results and exposing metrics
- RBAC
- Prometheus `ServiceMonitor`s (optional)

## Prerequisites

- Kubernetes 1.20+
- Helm 3.x
- Prometheus Operator for metrics (optional)

## Installation

```bash
helm repo add pitchbook oci://ghcr.io/pitchbook/charts && helm repo update
helm install kube-up pitchbook/kube-up \
  --namespace kube-up \
  --create-namespace
```

## Configuration

### Values Overview

The chart supports extensive configuration through the `values.yaml` file. Below are the key configuration sections.

| Parameter          | Description                | Default                     |
| ------------------ | -------------------------- | --------------------------- |
| `image.repository` | Container image repository | `ghcr.io/pitchbook/kube-up` |
| `image.tag`        | Container image tag        | `v1.0.0`                    |

### Manager Configuration

Configuration for the Kube Up Manager (operator component).

| Parameter                            | Description                                         | Default     |
| ------------------------------------ | --------------------------------------------------- | ----------- |
| `manager.config.workerLimit`         | Maximum concurrent Kopf workers                     | `20`        |
| `manager.config.logging.level`       | Logging level ("debug", "info", "warning", "error") | "info"      |
| `manager.resources.requests`         | Resource requests                                   |             |
| `manager.resources.limits`           | Resource limits                                     |             |
| `manager.deployment.metricsPort`     | Metrics port for Prometheus                         | `8000`      |
| `manager.deployment.healthPort`      | Health check port                                   | `8080`      |
| `manager.deployment.protocol`        | Port protocol                                       | `TCP`       |
| `manager.deployment.extraEnv`        | Additional environment variables                    | `[]`        |
| `manager.deployment.annotations`     | Additional pod annotations                          | `{}`        |
| `manager.serviceAccount.annotations` | Service account annotations                         | `{}`        |
| `manager.service.type`               | Service type                                        | `ClusterIP` |
| `manager.service.metricsPort`        | Service metrics port                                | `80`        |
| `manager.service.healthPort`         | Service health port                                 | `8080`      |

### API Configuration

Configuration for the Kube Up API component.

| Parameter                        | Description                                               | Default     |
| -------------------------------- | --------------------------------------------------------- | ----------- |
| `api.config.extraMetricsLabels`  | Additional labels to include on custom Prometheus metrics | `[]`        |
| `api.config.logging.level`       | Logging level (debug, info, warning, error)               | "info"      |
| `api.resources.requests`         | Resource requests                                         |             |
| `api.resources.limits`           | Resource limits                                           |             |
| `api.deployment.replicas`        | Number of API replicas                                    | `1`         |
| `api.deployment.port`            | Container port                                            | `8080`      |
| `api.deployment.protocol`        | Port protocol                                             | `TCP`       |
| `api.deployment.extraEnv`        | Additional environment variables                          | `[]`        |
| `api.deployment.annotations`     | Additional pod annotations                                | `{}`        |
| `api.serviceAccount.annotations` | Service account annotations                               | `{}`        |
| `api.pdb.enabled`                | Enable `PodDisruptionBudget`                              | `false`     |
| `api.pdb.minAvailable`           | Minimum available pods during disruption                  | `1`         |
| `api.service.type`               | Service type                                              | `ClusterIP` |
| `api.service.port`               | Service port                                              | `80`        |

### Ingress Configuration

Configuration for API ingress.

| Parameter                 | Description                    | Default |
| ------------------------- | ------------------------------ | ------- |
| `api.ingress.enabled`     | Enable ingress                 | `false` |
| `api.ingress.className`   | Ingress class name             | `""`    |
| `api.ingress.annotations` | Additional ingress annotations | `{}`    |
| `api.ingress.hosts`       | Ingress host rules             | `[]`    |
| `api.ingress.tls`         | TLS configuration              | `[]`    |

### ServiceMonitor Configuration

Configuration for Prometheus ServiceMonitors.

| Parameter                  | Description                            | Default      |
| -------------------------- | -------------------------------------- | ------------ |
| `serviceMonitor.namespace` | Namespace for ServiceMonitor resources | `monitoring` |
| `serviceMonitor.interval`  | Scrape interval                        | `15s`        |

## RBAC Permissions

### Manager Permissions

The Manager requires cluster-wide permissions to:

- `Event`s
  - `""` API group, `create` verb - for logging events
- `CronJob`s
  - `batch` API group, all verbs - for managing `CronJob`s
- Kube Up CRDs
  - `pitchbook.com`, all verbs
- `CustomResourceDefinition`s
  - `apiextensions.k8s.io` API group, `list` and `watch` verbs - for CRD discovery
- `Namespace`s
  - `""` API group, `list` and `watch` verbs - for namespace monitoring

### API Permissions

The API requires cluster-wide permissions to:

- `Pod`s
  - `""` API group, `get` and `list` verbs - for identifying check pods by IP/name
- `Job`s
  - `batch` API group, `get` verb - for job information
- Kube Up CRDs
  - `pitchbook.com` API group, all verbs - for reading and updating `KubeUpState`s
