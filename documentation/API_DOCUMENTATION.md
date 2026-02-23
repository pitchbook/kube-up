# Kube Up API

## Overview

The backend API, responsible for updating and reporting the statuses of `KubeUpCheck`s.

## Configuration

The API can be configured using the following environment variables:

| Variable               | Default   | Description                                         |
| ---------------------- | --------- | --------------------------------------------------- |
| `HOST_ADDRESS`         | `0.0.0.0` | Address to bind the server to                       |
| `HOST_PORT`            | `8080`    | Port to bind the server to                          |
| `TIMEOUT`              | `60`      | Request timeout in seconds                          |
| `LOG_LEVEL`            | "info"    | Logging level ("debug", "info", "warning", "error") |
| `NAMESPACE`            | "kube-up" | Namespace to watch for CRDs in                      |
| `EXTRA_METRICS_LABELS` | null      | Extra labels to add to metrics                      |

## API

### GET /synthetics

Retrieve the status of all Kube Up synthetic checks.

#### Request

- Method: `GET`
- Path: `/synthetics`
- Query Parameters: None
- Body: None

#### Response

Status Code: `200 OK`

```json
{
  "ok": true,
  "errors": [],
  "checkDetails": [
    {
      "ok": true,
      "errors": [],
      "name": "test-check",
      "namespace": "kube-up",
      "lastRun": "2024-01-27T10:30:00.000Z",
      "runDuration": "5s",
      "authoritativePod": "test-check-28450123-abc12",
      "labels": {
        "owner": "platform-engineering",
        "service": "my-service",
        "severity": "1"
      },
      "customMetrics": [
        {
          "name": "ttfb",
          "value": 150,
          "labels": [
            {
              "name": "endpoint",
              "value": "/health"
            }
          ]
        }
      ]
    }
  ]
}
```

**Response Schema:**

| Field          | Type                   | Description                                       |
| -------------- | ---------------------- | ------------------------------------------------- |
| `ok`           | boolean                | Overall status - `true` if all checks are passing |
| `errors`       | array[string]          | List of errors encountered across all checks      |
| `checkDetails` | array[SyntheticsState] | Detailed status of each check                     |

**SyntheticsState Object:**

| Field              | Type                         | Description                                           |
| ------------------ | ---------------------------- | ----------------------------------------------------- |
| `ok`               | boolean                      | Whether this specific check succeeded                 |
| `errors`           | array[string]                | List of errors for this check                         |
| `name`             | string                       | Name of the KubeUpCheck resource                      |
| `namespace`        | string                       | Kubernetes namespace containing the check             |
| `lastRun`          | string (ISO 8601)            | Timestamp of last check execution (nullable)          |
| `runDuration`      | string                       | Duration of last run (e.g., "5s", "1m30s") (nullable) |
| `authoritativePod` | string                       | Name of the pod that last ran the check (nullable)    |
| `labels`           | object                       | Extra metrics labels defined in KubeUpCheck spec      |
| `customMetrics`    | array[SyntheticCustomMetric] | Custom metrics reported by the check                  |

**SyntheticCustomMetric Object:**

| Field    | Type                              | Description                                 |
| -------- | --------------------------------- | ------------------------------------------- |
| `name`   | string                            | Metric name (e.g., "ttfb", "response_time") |
| `value`  | integer                           | Metric value                                |
| `labels` | array[SyntheticCustomMetricLabel] | Additional labels for this metric           |

**SyntheticCustomMetricLabel Object:**

| Field   | Type   | Description |
| ------- | ------ | ----------- |
| `name`  | string | Label name  |
| `value` | string | Label value |

**Example cURL:**

```bash
curl -X GET http://localhost:8080/synthetics
```

### POST /synthetics/results

Submit results and custom metrics from a synthetic check run. This endpoint is called by synthetic check pods to report
their execution results.

#### Request

- Method: `POST`
- Path: `/synthetics/results`
- Query Parameters: None

```json
{
  "ok": true,
  "errors": [],
  "podName": "test-check-28450123-abc12",
  "customMetrics": [
    {
      "name": "ttfb",
      "value": 150,
      "labels": [
        {
          "name": "endpoint",
          "value": "/api/health"
        }
      ]
    },
    {
      "name": "response_time",
      "value": 250,
      "labels": []
    }
  ]
}
```

**Request Schema:**

| Field           | Type                         | Required | Description                                                                    |
| --------------- | ---------------------------- | -------- | ------------------------------------------------------------------------------ |
| `ok`            | boolean                      | Yes      | Whether the synthetic check succeeded                                          |
| `errors`        | array[string]                | No       | List of errors encountered during the check (default: `[]`)                    |
| `podName`       | string                       | No       | Name of the pod running the check. If null, will be determined from request IP |
| `customMetrics` | array[SyntheticCustomMetric] | No       | Custom metrics to report (default: `[]`)                                       |

**Notes:**

- If `podName` is not provided, the API will look up the pod using the request IP address from the `X-Forwarded-For`
  header or client IP
- The pod must have the following labels set:
  - `job-name`: The Kubernetes Job name
  - `kube-up.pitchbook.com/owning-cronjob`: The KubeUpCheck name
  - `kube-up.pitchbook.com/timeout`: The timeout value (optional)
- Pod must exist in the same namespace as the KubeUpCheck (configured via `NAMESPACE`)

#### Response

Status Code: `201 Created`

Body: Empty

**Error Responses:**

Status Code: `404 Not Found`

Occurs when the pod cannot be found by name or IP.

```json
{
  "message": "Pod 'test-check-28450123-abc12' not found"
}
```

**Example cURL:**

```bash
curl -X POST http://localhost:8080/synthetics/results \
  -H "Content-Type: application/json" \
  -d '{
    "ok": true,
    "errors": [],
    "podName": "test-check-28450123-abc12",
    "customMetrics": [
      {
        "name": "ttfb",
        "value": 150,
        "labels": []
      }
    ]
  }'
```

**Example from within a synthetic check pod:**

```bash
#!/bin/bash

# Run your check
CHECK_RESULT=$(./run_check.sh)

# Report results
curl -X POST http://kube-up-api/synthetics/results \
  -H "Content-Type: application/json" \
  -d "{
    \"ok\": true,
    \"errors\": [],
    \"customMetrics\": [
      {
        \"name\": \"response_time\",
        \"value\": 250,
        \"labels\": []
      }
    ]
  }"
```
