from asyncio import sleep
from datetime import UTC, datetime

import orjson
from kubernetes_asyncio.client import BatchV1Api, CustomObjectsApi
from kubernetes_asyncio.client.exceptions import ApiException
from structlog import get_logger

from app.api.labels import filter_labels
from app.common.client import API_CLIENT
from app.common.logs import log_exception
from app.config import SETTINGS
from app.models import KUNotFoundError, ResultsRequest, SyntheticLabels, SyntheticsState

KU_LABEL = "app.kubernetes.io/managed-by=kube-up"

logger = get_logger()


async def update_state(results: ResultsRequest) -> None:
    """
    Update the status fields of a KUState

    :param results: Run results from Job
    :return: Check run duration, Job labels
    """

    # Work around content-type bug in kubernetes_asyncio patching
    API_CLIENT.client.set_default_header("Content-Type", "application/merge-patch+json")

    k8s_batch = BatchV1Api(API_CLIENT.client)
    # Retrieve Job to infer start time and duration
    try:
        job = await k8s_batch.read_namespaced_job(name=results.job_name or "", namespace=SETTINGS.namespace)
    except ApiException as ex:
        if ex.status == 404:
            log_exception(ex, "Job not found", jobName=results.job_name)
            raise KUNotFoundError(f"Job '{results.job_name}' not found") from ex
        raise
    start_time = job.status.start_time
    # Use datetime.now() because job will technically still be in process when call to API is made
    run_duration = int((datetime.now(UTC) - start_time).total_seconds())

    # Check timeout if job passed
    if results.ok:
        timed_out = results.has_timed_out(run_duration)
        if timed_out:
            results.ok = False
            results.errors.insert(0, "KubeUpTimeoutError")
            logger.info(
                "Check exceeded timeout",
                kuCheckName=results.check_name,
                kuCheckTimeout=results.timeout,
                kuCheckRunDuration=run_duration,
            )
    else:
        logger.info("Check failed", kuCheckName=results.check_name, kuCheckErrors=results.errors)

    k8s_crd = CustomObjectsApi(API_CLIENT.client)
    # kwargs reused several times
    crd_kwargs = {
        "name": results.check_name or "",
        "namespace": SETTINGS.namespace,
        "group": SETTINGS.ku_group,
        "version": SETTINGS.ku_api_version,
        "plural": SETTINGS.ku_state_plural,
    }
    try:
        state = await k8s_crd.get_namespaced_custom_object(**crd_kwargs)
    except ApiException as ex:
        if ex.status == 404:
            log_exception(ex, "KU State not found", kuStateName=results.check_name)
            raise KUNotFoundError(f"KU State '{results.check_name}' not found") from ex
        raise

    state["spec"]["ok"] = results.ok
    state["spec"]["errors"] = results.errors
    state["spec"]["lastRun"] = start_time
    state["spec"]["runDuration"] = f"{run_duration}s"
    state["spec"]["authoritativePod"] = results.pod_name
    state["spec"]["customMetrics"] = [custom_metric.model_dump() for custom_metric in results.custom_metrics]
    logger.debug("generated updated KUState manifest", kuState=state)
    try:
        await k8s_crd.patch_namespaced_custom_object(body=state, **crd_kwargs)
    except ApiException as ex:
        # Race condition can occur if KUState is updated by another process at same time as API call
        # Wait 1 second and retry
        if ex.status == 409:
            log_exception(ex, "KU State modified, retrying", kuStateName=results.check_name)
            await sleep(1)
            state = await k8s_crd.get_namespaced_custom_object(**crd_kwargs)
            await k8s_crd.patch_namespaced_custom_object(body=state, **crd_kwargs)
        else:
            raise


async def get_check_statuses() -> tuple[bool, list[str], list[SyntheticsState]]:
    """
    Get all KU State objects

    :return: overall ok status, overall errors, list of states
    """

    overall_status = True
    all_errors = []
    state_models = []

    k8s_crd = CustomObjectsApi(API_CLIENT.client)
    try:
        k8s_states = await k8s_crd.list_namespaced_custom_object(
            namespace=SETTINGS.namespace,
            group=SETTINGS.ku_group,
            version=SETTINGS.ku_api_version,
            plural=SETTINGS.ku_state_plural,
        )
    except ApiException as ex:
        if ex.status == 429:
            try:
                response = orjson.loads(ex.body) if ex.body else {}
                sleep_duration = response["details"]["retryAfterSeconds"]
            except (AttributeError, orjson.JSONDecodeError, KeyError, TypeError) as inner_ex:
                log_exception(inner_ex, "failed to retrieve retryAfterSeconds, defaulting to 1 second")
                sleep_duration = 1
            log_exception(ex, f"rate limited, retrying after {sleep_duration} second(s)")
            await sleep(sleep_duration)
            k8s_states = await k8s_crd.list_namespaced_custom_object(
                namespace=SETTINGS.namespace,
                group=SETTINGS.ku_group,
                version=SETTINGS.ku_api_version,
                plural=SETTINGS.ku_state_plural,
            )
        else:
            raise
    for state in k8s_states["items"]:
        try:
            state_model = SyntheticsState(
                name=state["metadata"]["name"],
                namespace=state["metadata"]["namespace"],
                labels=SyntheticLabels(**filter_labels(state["metadata"]["labels"], SETTINGS.extra_metrics_labels)),
                ok=state["spec"]["ok"],
                errors=state["spec"]["errors"],
                # Ensure backwards compatibility with old States
                custom_metrics=state["spec"].get("customMetrics", []),
                # These fields can be null if check hasn't run, and thus don't get included in API response
                last_run=state["spec"].get("lastRun"),
                run_duration=state["spec"].get("runDuration"),
                authoritative_pod=state["spec"].get("authoritativePod"),
            )
        except Exception as ex:
            log_exception(ex, "error creating SyntheticsState from KU State", kuStateData=str(state))
            raise
        if not state_model.ok:
            overall_status = False
        if state_model.errors:
            all_errors.extend(state_model.errors)
        state_models.append(state_model)

    return overall_status, all_errors, state_models
