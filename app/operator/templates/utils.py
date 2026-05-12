import os
from copy import deepcopy

import yaml

from app.config import SETTINGS

BASE_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
with open(os.path.join(BASE_DIR, "cronjob.yaml")) as yaml_in:
    CRONJOB = yaml.safe_load(yaml_in)

HOST_ENV = [
    {
        "name": SETTINGS.api_url_env_var,
        "value": f"http://{SETTINGS.api_service_name}.{SETTINGS.namespace}/synthetics/results",
    }
]


def get_cronjob_template(
    name: str, namespace: str, interval_min: str | int, suspend: bool, pod_spec: dict, extra_labels: dict
) -> dict:
    """
    Template out a Cronjob using provided values

    :param name: cronjob name
    :param namespace: cronjob namespace
    :param interval_min: interval between runs in minutes (as string or int)
    :param suspend: whether the cronjob should be disabled
    :param pod_spec: pod spec
    :param extra_labels: extra labels for metrics and Kubernetes objects
    :return: Cronjob in dict form
    """

    cronjob = deepcopy(CRONJOB)
    cronjob["metadata"]["name"] = name
    cronjob["metadata"]["namespace"] = namespace
    cronjob["metadata"]["labels"].update(extra_labels)
    cronjob["spec"]["schedule"] = f"*/{interval_min} * * * *"
    cronjob["spec"]["suspend"] = suspend
    cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"] = pod_spec
    cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["restartPolicy"] = "Never"
    cronjob["spec"]["jobTemplate"]["spec"]["template"]["metadata"]["labels"].update(extra_labels)
    if cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0].get("env"):
        cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["env"].extend(HOST_ENV)
    else:
        cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["env"] = HOST_ENV

    return cronjob


KU_STATE_PLURAL = "kustates"
with open(os.path.join(BASE_DIR, "kustate.yaml")) as yaml_in:
    KU_STATE = yaml.safe_load(yaml_in)


def get_ku_state_template(name: str, namespace: str, extra_labels: dict, ku_state: dict | None = None) -> dict:
    """
    Template out a Kube Up State CRD using provided values

    :param name: cronjob name
    :param namespace: cronjob namespace
    :param extra_labels: extra labels for metrics and Kubernetes objects
    :param ku_state: Kube Up State resource
    :return: Kube Up State in dict form
    """

    if ku_state is None:
        ku_state = deepcopy(KU_STATE)
    ku_state["metadata"]["name"] = name
    ku_state["metadata"]["namespace"] = namespace
    ku_state["metadata"]["labels"].update(extra_labels)

    return ku_state


KU_GROUP, KU_API_VERSION = KU_STATE["apiVersion"].split("/")
