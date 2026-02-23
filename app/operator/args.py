import kopf

from app.common.timestrs import timestr_to_minutes, timestr_to_seconds


def get_ku_args(spec: dict, name: str) -> tuple[str, bool, dict, dict]:
    """
    Get common KU args for cronjobs and status objects

    :param spec: KUCheck spec
    :param name: KUCheck name
    :return: interval (as string minutes), suspend, pod spec, and extra labels
    """

    interval = timestr_to_minutes(spec.get("runInterval", "5m"))
    suspend = spec.get("suspend", False)
    timeout = timestr_to_seconds(spec.get("timeout", interval))
    pod_spec = spec.get("podSpec", {})
    if not pod_spec:
        raise kopf.PermanentError("podSpec must be set")
    extra_labels = spec.get("extraLabels", {})
    if extra_labels is None:
        extra_labels = {}
    # Append owning-cronjob label for use in filtering in API
    extra_labels["kube-up.pitchbook.com/owning-cronjob"] = name
    # Append timeout label for determining if a job has exceeded its timeout
    extra_labels["kube-up.pitchbook.com/timeout"] = str(timeout)

    return interval, suspend, pod_spec, extra_labels
