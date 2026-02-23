# Kube Up Manager

## Overview

The operator portion of Kube Up, responsible for monitoring the state of the CRDs and synchronizing them with the
corresponding Kubernetes `CronJob`s and `KubeUpState`s.

## Configuration

The Manager can be configured using the following environment variables:

| Variable            | Default   | Description                                         |
| ------------------- | --------- | --------------------------------------------------- |
| `METRICS_PORT`      | `8000`    | Port to bind the metrics server to                  |
| `LOG_LEVEL`         | "info"    | Logging level ("debug", "info", "warning", "error") |
| `NAMESPACE`         | "kube-up" | Namespace to watch for CRDs in                      |
| `KOPF_WORKER_LIMIT` | `20`      | Kopf worker limit                                   |

## CRDS

### `KubeUpCheck`

The `KubeUpCheck` CRD defines a synthetic check that runs on a schedule. When created, the Kube Up Manager creates a
corresponding Kubernetes `CronJob` and `KubeUpState` resource.

#### Spec

The `spec` section defines the desired state of the synthetic check.

| Field              | Type    | Required | Default | Description                                                                                         |
| ------------------ | ------- | -------- | ------- | --------------------------------------------------------------------------------------------------- |
| `runInterval`      | string  | **Yes**  | -       | Kubernetes duration string indicating how frequently the check should run (e.g., "5m", "1h", "30s") |
| `timeout`          | string  | **Yes**  | -       | Kubernetes duration string after which a check should be considered failed (e.g., "1m", "30s")      |
| `podSpec`          | object  | **Yes**  | -       | Standard Kubernetes PodSpec defining the container(s) to run for the check                          |
| `extraLabels`      | object  | No       | `{}`    | Map of additional labels to add to Prometheus metrics                                               |
| `extraAnnotations` | object  | No       | `{}`    | Map of additional annotations to add to created resources                                           |
| `suspend`          | boolean | No       | `false` | Whether the check is disabled/suspended                                                             |

**runInterval** (required)

Defines how often the synthetic check runs. Uses Kubernetes duration format.

- Examples: `"1m"`, `"5m"`, `"15m"`, `"1h"`, `"30s"`
- Converted to a crontab for the CronJob schedule

**timeout** (required)

Maximum duration for a check run before it's considered failed.

- Examples: `"30s"`, `"1m"`, `"2m30s"`
- Checked by API when receiving results to determine if check timed out (i.e. failed)

**podSpec** (required)

Standard Kubernetes [PodSpec](https://kubernetes.io/docs/reference/generated/kubernetes-api/latest/#podspec-v1-core) object. Defines the container(s) that perform the synthetic check.

**extraLabels** (optional)

Key-value map of additional labels to include in Prometheus metrics.

Common labels:

- `owner`: Team or individual responsible for the check
- `service`: Service being monitored
- `severity`: Incident severity level if check fails (e.g., "1", "2", "3")
- `team`: Team name

These labels appear on all Prometheus metrics for this check:

- `kube_up_ok{name, namespace, ...<extraLabels>}`
- `kube_up_last_run{name, namespace, ...<extraLabels>}`
- `kube_up_run_duration{name, namespace, ...<extraLabels>}`
- `kube_up_custom_*{name, namespace, ...<extraLabels>, ...<customLabels>}`

**extraAnnotations** (optional)

Key-value map of additional annotations to add to the created `CronJob` resources.

**suspend** (optional)

Boolean flag to temporarily disable the check without deleting it. When `true`:

- CronJob is suspended (no new runs scheduled)
- Existing KubeUpState is retained
- Metrics continue to be exposed with last known state

#### Examples

**Minimal**

```yaml
apiVersion: pitchbook.com/v1
kind: KubeUpCheck
metadata:
  name: simple-check
  namespace: kube-up
spec:
  runInterval: 1m
  timeout: 30s
  extraLabels:
    owner: my-team
    service: my-service
    severity: "2"
  podSpec:
    containers:
      - name: check
        image: example-check:latest
    restartPolicy: Never
```

**Complete**

```yaml
apiVersion: pitchbook.com/v1
kind: KubeUpCheck
metadata:
  name: complete-check
  namespace: kube-up
spec:
  runInterval: 5m
  timeout: 2m
  suspend: false
  extraLabels:
    owner: my-team
    service: my-service
    severity: "2"
  extraAnnotations:
    description: "Complete check for Example API"
  podSpec:
    containers:
      - name: health-check
        image: my-registry.example.com/synthetic-checks:v1.2.3
        imagePullPolicy: IfNotPresent
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 256Mi
            cpu: 200m
        env:
          # Check-specific configuration
          - name: TARGET_URL
            value: https://api.example.com/health
          - name: EXPECTED_STATUS
            value: "200"
          - name: CHECK_TIMEOUT
            value: "10"
          # Optional: load secrets
          - name: API_KEY
            valueFrom:
              secretKeyRef:
                name: api-credentials
                key: api-key
    restartPolicy: Never
    terminationGracePeriodSeconds: 10
```

#### Printer Columns

When listing KubeUpChecks, the following columns are displayed:

| Column       | Description                | JSON Path                     |
| ------------ | -------------------------- | ----------------------------- |
| NAME         | Resource name              | `.metadata.name`              |
| RUN INTERVAL | How often check runs       | `.spec.runInterval`           |
| TIMEOUT      | Check timeout              | `.spec.timeout`               |
| SUSPEND      | Whether check is suspended | `.spec.suspend`               |
| AGE          | Time since creation        | `.metadata.creationTimestamp` |

### `KubeUpState`

The `KubeUpState` CRD holds the current status and results of a `KubeUpCheck`. It is automatically created and managed
by the Kube Up Manager when a `KubeUpCheck` is created, and updated by the Kube Up API when check results are submitted.

#### Spec

The `spec` section holds the state data for the check.

| Field              | Type              | Required | Nullable | Description                                          |
| ------------------ | ----------------- | -------- | -------- | ---------------------------------------------------- |
| `ok`               | boolean           | No       | No       | Whether the last check run succeeded                 |
| `errors`           | array[string]     | No       | No       | List of errors from the last check run               |
| `lastRun`          | string (ISO 8601) | No       | Yes      | Timestamp of the last check execution                |
| `runDuration`      | string            | No       | Yes      | Duration of the last check run (e.g., "5s", "1m30s") |
| `authoritativePod` | string            | No       | Yes      | Name of the pod that executed the last check         |
| `customMetrics`    | array[object]     | No       | No       | Custom metrics reported by the check                 |

##### Custom Metrics Schema

Each item in the `customMetrics` array has the following structure:

| Field    | Type          | Description            |
| -------- | ------------- | ---------------------- |
| `name`   | string        | Metric name            |
| `value`  | integer       | Metric value           |
| `labels` | array[object] | Metric-specific labels |

Each label object has:

| Field   | Type   | Description |
| ------- | ------ | ----------- |
| `name`  | string | Label name  |
| `value` | string | Label value |

#### Printer Columns

When listing KubeUpStates, the following columns are displayed:

| Column       | Description           | JSON Path                     |
| ------------ | --------------------- | ----------------------------- |
| NAME         | Resource name         | `.metadata.name`              |
| OK           | Check status          | `.spec.ok`                    |
| LAST RUN     | Timestamp of last run | `.spec.lastRun`               |
| RUN DURATION | Duration of last run  | `.spec.runDuration`           |
| AGE          | Time since creation   | `.metadata.creationTimestamp` |

#### Important Notes

Do not manually create, edit, or delete `KubeUpState` resources, they are managed by: - Kube Up Manager (creation, deletion, and updates when `KubeUpCheck` changes) - Kube Up API (updated when check results are submitted)

## Troubleshooting

### Check not running

```bash
# 1. Verify KubeUpCheck exists
kubectl get kucheck example-check -n kube-up

# 2. Check if CronJob was created
kubectl get cronjob -n kube-up | grep example-check

# 3. Check if check is suspended
kubectl get kucheck example-check -n kube-up -o jsonpath='{.spec.suspend}'

# 4. Check CronJob status
kubectl describe cronjob example-check -n kube-up

# 5. Check recent Jobs
kubectl get jobs -n kube-up | grep example-check
```

### Check failing

```bash
# 1. Check KubeUpState for errors
kubectl get kustate example-check -n kube-up -o yaml

# 2. Look at recent pod logs
kubectl logs -n kube-up -l kube-up.pitchbook.com/owning-cronjob=example-check --tail=50

# 3. Check pod status
kubectl get pods -n kube-up -l kube-up.pitchbook.com/owning-cronjob=example-check

# 4. Describe the pod for events
kubectl describe pod <pod-name> -n kube-up
```

### Check not reporting results

```bash
# 1. Verify pod can reach API
kubectl exec -n kube-up <pod-name> -- \
  curl -v http://kube-up-api.kube-up/healthcheck

# 2. Check API logs
kubectl logs -n kube-up -l app=kube-up-api --tail=50

# 3. Verify KU_API_URL is set correctly
kubectl get kucheck example-check -n kube-up -o yaml | grep KU_API_URL

# 4. Check network policies
kubectl get networkpolicy -n kube-up
```

### Metrics not showing up

```bash
# 1. Check if KubeUpState exists and has data
kubectl get kustate example-check -n kube-up -o yaml

# 2. Query metrics endpoint directly
kubectl port-forward -n kube-up svc/kube-up-api 8080:80
curl http://localhost:8080/metrics | grep example-check

# 3. Verify ServiceMonitor is configured
kubectl get servicemonitor -n kube-up

# 4. Check Prometheus scrape config
kubectl get prometheus -A -o yaml | grep kube-up
```

## Migration and Updates

### Updating a KubeUpCheck

When you update a KubeUpCheck:

- The Kube Up Manager detects the change
- The associated `CronJob` is updated
- The `KubeUpState` is updated if necessary
- New `Job`s will use the updated specification

### Deleting a KubeUpCheck

When you delete a KubeUpCheck:

- The `CronJob` is deleted
- The `KubeUpState` is deleted
- Associated `Job`s and `Pod`s are cleaned up by Kubernetes garbage collection

```bash
kubectl delete kucheck example-check -n kube-up
```
