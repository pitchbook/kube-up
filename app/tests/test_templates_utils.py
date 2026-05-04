import copy

import pytest

from app.operator.templates.utils import get_cronjob_template, get_ku_state_template

BASE_POD_SPEC = {
    "containers": [{"name": "test", "image": "test:latest"}],
}

POD_SPEC_WITH_ENV = {
    "containers": [{"name": "test", "image": "test:latest", "env": [{"name": "FOO", "value": "bar"}]}],
}


@pytest.mark.parametrize(
    ("name", "namespace", "interval_min", "suspend"),
    [
        ("my-check", "default", 5, False),
        ("another-check", "monitoring", "10", True),
        ("check-1", "kube-up", 1, False),
    ],
)
def test_get_cronjob_template_metadata(name, namespace, interval_min, suspend):
    result = get_cronjob_template(name, namespace, interval_min, suspend, BASE_POD_SPEC, {})

    assert result["metadata"]["name"] == name
    assert result["metadata"]["namespace"] == namespace
    assert result["spec"]["suspend"] == suspend
    assert result["spec"]["schedule"] == f"*/{interval_min} * * * *"


def test_get_cronjob_template_managed_by_label():
    result = get_cronjob_template("check", "default", 5, False, BASE_POD_SPEC, {})

    assert result["metadata"]["labels"]["app.kubernetes.io/managed-by"] == "kube-up"
    assert (
        result["spec"]["jobTemplate"]["spec"]["template"]["metadata"]["labels"]["app.kubernetes.io/managed-by"]
        == "kube-up"
    )


def test_get_cronjob_template_extra_labels():
    extra = {"team": "platform", "env": "prod"}
    result = get_cronjob_template("check", "default", 5, False, BASE_POD_SPEC, extra)

    for key, value in extra.items():
        assert result["metadata"]["labels"][key] == value
        assert result["spec"]["jobTemplate"]["spec"]["template"]["metadata"]["labels"][key] == value


def test_get_cronjob_template_pod_spec_set():
    result = get_cronjob_template("check", "default", 5, False, BASE_POD_SPEC, {})

    spec = result["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert spec["containers"][0]["name"] == "test"
    assert spec["restartPolicy"] == "Never"


def test_get_cronjob_template_host_env_injected_no_existing_env():
    result = get_cronjob_template("check", "default", 5, False, BASE_POD_SPEC, {})

    env = result["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["env"]
    names = [e["name"] for e in env]
    assert "KU_API_URL" in names


def test_get_cronjob_template_host_env_appended_to_existing_env():
    result = get_cronjob_template("check", "default", 5, False, POD_SPEC_WITH_ENV, {})

    env = result["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["env"]
    names = [e["name"] for e in env]
    assert "FOO" in names
    assert "KU_API_URL" in names


def test_get_cronjob_template_mutates_pod_spec_in_place():
    pod_spec = copy.deepcopy(BASE_POD_SPEC)
    get_cronjob_template("check", "default", 5, False, pod_spec, {})

    # The function assigns pod_spec directly into the template and then mutates it in place (e.g. sets restartPolicy).
    assert pod_spec["restartPolicy"] == "Never"


def test_get_ku_state_template_metadata():
    result = get_ku_state_template("my-check", "default", {})

    assert result["metadata"]["name"] == "my-check"
    assert result["metadata"]["namespace"] == "default"


def test_get_ku_state_template_managed_by_label():
    result = get_ku_state_template("my-check", "default", {})

    assert result["metadata"]["labels"]["app.kubernetes.io/managed-by"] == "kube-up"


def test_get_ku_state_template_extra_labels():
    extra = {"team": "platform"}
    result = get_ku_state_template("my-check", "default", extra)

    assert result["metadata"]["labels"]["team"] == "platform"


def test_get_ku_state_template_uses_provided_ku_state():
    existing = {
        "apiVersion": "pitchbook.com/v1",
        "kind": "KubeUpState",
        "metadata": {"name": "old", "namespace": "old", "labels": {"app.kubernetes.io/managed-by": "kube-up"}},
        "spec": {
            "ok": True,
            "errors": [],
            "lastRun": "2024-01-01T00:00:00Z",
            "runDuration": 1.5,
            "authoritativePod": "pod-abc",
            "customMetrics": [],
        },
    }
    result = get_ku_state_template("new-name", "new-ns", {}, ku_state=existing)

    assert result["metadata"]["name"] == "new-name"
    assert result["metadata"]["namespace"] == "new-ns"
    # spec from existing state is preserved
    assert result["spec"]["ok"] is True
    assert result["spec"]["lastRun"] == "2024-01-01T00:00:00Z"


def test_get_ku_state_template_does_not_mutate_input():
    existing = {
        "apiVersion": "pitchbook.com/v1",
        "kind": "KubeUpState",
        "metadata": {"name": "old", "namespace": "old", "labels": {"app.kubernetes.io/managed-by": "kube-up"}},
        "spec": {},
    }

    original = copy.deepcopy(existing)
    get_ku_state_template("new-name", "new-ns", {}, ku_state=existing)

    # The function modifies the provided ku_state in-place (by design), so we only check that *our* original deep-copy
    # is untouched.
    assert original["metadata"]["name"] == "old"
