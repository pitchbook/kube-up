import dataclasses
import os

import kopf
import kubernetes_asyncio
from kubernetes_asyncio.client import BatchV1Api, CustomObjectsApi
from prometheus_client import start_http_server
from structlog import get_logger

from app.common.client import API_CLIENT
from app.common.logs import log_exception, log_unhandled_exceptions
from app.config import SETTINGS
from app.operator.args import get_ku_args
from app.operator.templates.utils import (
    KU_API_VERSION,
    KU_GROUP,
    KU_STATE_PLURAL,
    get_cronjob_template,
    get_ku_state_template,
)

logger = get_logger()

N_RETRIES = None
CREATE_CONTENT_TYPE = "application/json"
MERGE_CONTENT_TYPE = "application/merge-patch+json"

logger.info("watching resources in namespace", namespace=SETTINGS.namespace)

try:
    WORKER_LIMIT = int(os.getenv("KOPF_WORKER_LIMIT", "20"))
except ValueError as ex:
    log_exception(ex, "invalid KOPF_WORKER_LIMIT value, using default of 20")
    WORKER_LIMIT = 20


@kopf.on.login(errors=kopf.ErrorsMode.PERMANENT)  # type: ignore[arg-type]
async def login_fn(**kwargs):
    if "KUBERNETES_PORT" in os.environ:
        result = kopf.login_with_service_account(**kwargs)
    else:
        result = kopf.login_via_client(logger=logger, **kwargs)

    # Workaround for Python 3.13 SSL change
    if result is not None:
        result = dataclasses.replace(result, insecure=True)

    return result


@kopf.on.startup()  # type: ignore[arg-type]
async def startup_fn(**kwargs) -> None:
    """
    Load Kubernetes config and API client on startup
    """

    if "KUBERNETES_PORT" in os.environ:
        logger.debug("using in-cluster config")
        kubernetes_asyncio.config.load_incluster_config()
    else:
        logger.debug("using local config")
        await kubernetes_asyncio.config.load_kube_config()

    await API_CLIENT.load()


async def _cleanup_resources(name: str, namespace: str) -> None:
    """
    Cleanup corresponding Cronjob and KU State object after KU Check deletion

    :param name: KU Check name
    """

    logger.info("attempting to clean up KU resources", resourceName=name)
    try:
        k8s_batch = BatchV1Api(API_CLIENT.client)
        await k8s_batch.delete_namespaced_cron_job(name=name, namespace=namespace)
    except Exception as ex:
        if isinstance(ex, kubernetes_asyncio.client.exceptions.ApiException) and ex.status == 404:
            logger.warn("Cronjob not found", resourceName=name)
        else:
            log_unhandled_exceptions(ex, "DELETE", "_cleanup_resources", "error deleting Cronjob")
    else:
        logger.info("deleted cronjob resource", resourceName=name)

    try:
        k8s_crd = CustomObjectsApi(API_CLIENT.client)
        await k8s_crd.delete_namespaced_custom_object(
            name=name,
            group=KU_GROUP,
            version=KU_API_VERSION,
            plural=KU_STATE_PLURAL,
            namespace=namespace,
        )
    except Exception as ex:
        if isinstance(ex, kubernetes_asyncio.client.exceptions.ApiException) and ex.status == 404:
            logger.warn("KU State resource not found", resourceName=name)
        else:
            log_unhandled_exceptions(ex, "DELETE", "_cleanup_resources", "error deleting KU State")
    else:
        logger.info("deleted KU State resource", resourceName=name)

    logger.info("clean up complete", resourceName=name)


@kopf.on.create("kuchecks", retries=N_RETRIES)  # type: ignore[arg-type]
async def create_ku_resources(spec: dict, name: str, namespace: str, **kwargs: dict) -> None:
    """
    When a KU Check is created, create a corresponding Cronjob and KU State object

    :param spec: KUCheck spec
    :param name: KUCheck name
    :param namespace: KUCheck namespace
    :param kwargs: KOPF kwargs
    """

    cronjob = {}
    ku_state = {}
    k8s_crd = {}

    logger.debug("creating KU resources", resourceName=name)

    try:
        interval, suspend, pod_spec, extra_labels = get_ku_args(spec, name)

        cronjob = get_cronjob_template(name, namespace, interval, suspend, pod_spec, extra_labels)
        kopf.adopt(cronjob)
        logger.debug("created cronjob data", resourceName=name, cronjobData=str(cronjob))

        k8s_batch = BatchV1Api(API_CLIENT.client)
        await k8s_batch.create_namespaced_cron_job(
            namespace=namespace,
            body=cronjob,  # type: ignore[arg-type]
            _content_type=CREATE_CONTENT_TYPE,
        )
        logger.info("created cronjob resource", resourceName=name)

        ku_state = get_ku_state_template(name, namespace, extra_labels)
        kopf.adopt(ku_state)
        logger.debug("created KU State data", resourceName=name, kuStateData=str(cronjob))

        k8s_crd = CustomObjectsApi(API_CLIENT.client)
        await k8s_crd.create_namespaced_custom_object(
            group=KU_GROUP,
            version=KU_API_VERSION,
            plural=KU_STATE_PLURAL,
            namespace=namespace,
            body=ku_state,
            _content_type=CREATE_CONTENT_TYPE,
        )
        logger.info("created KU State resource", resourceName=name)

    except Exception as ex:
        log_unhandled_exceptions(
            ex,
            "POST",
            "create_ku_resources",
            "error creating KU resources",
            cronjob=str(cronjob),
            kuState=str(ku_state),
            crd=str(k8s_crd),
        )
        await _cleanup_resources(name, namespace)

        raise

    logger.debug("creation complete", resourceName=name)


@kopf.on.update("kuchecks", retries=N_RETRIES)  # type: ignore[arg-type]
async def update_ku_resources(spec: dict, name: str, namespace: str, **kwargs: dict) -> None:
    """
    When a KU Check is updated, update the corresponding Cronjob and KU State object

    :param spec: KUCheck spec
    :param name: KUCheck name
    :param namespace: KUCheck namespace
    :param kwargs: KOPF kwargs
    """

    cronjob = {}
    ku_state = {}
    k8s_crd = {}

    logger.debug("updating KU resources", resourceName=name)

    try:
        interval, suspend, pod_spec, extra_labels = get_ku_args(spec, name)

        cronjob = get_cronjob_template(name, namespace, interval, suspend, pod_spec, extra_labels)
        kopf.adopt(cronjob)
        logger.debug("generated updated cronjob data", resourceName=name, cronjobData=str(cronjob))

        k8s_batch = BatchV1Api(API_CLIENT.client)
        try:
            await k8s_batch.patch_namespaced_cron_job(
                name=name,
                namespace=namespace,
                body=cronjob,
                _content_type=MERGE_CONTENT_TYPE,
            )
            logger.info("patched cronjob resource", resourceName=name)
        except Exception as ex:
            if isinstance(ex, kubernetes_asyncio.client.exceptions.ApiException) and ex.status == 404:
                logger.warn("Cronjob not found, attempting to create", resourceName=name)
                await k8s_batch.create_namespaced_cron_job(
                    namespace=namespace,
                    body=cronjob,  # type: ignore[arg-type]
                    _content_type=CREATE_CONTENT_TYPE,
                )
                logger.info("created cronjob resource", resourceName=name)
            else:
                raise

        k8s_crd = CustomObjectsApi(API_CLIENT.client)
        try:
            existing_ku_state = await k8s_crd.get_namespaced_custom_object(
                name=name,
                group=KU_GROUP,
                version=KU_API_VERSION,
                plural=KU_STATE_PLURAL,
                namespace=namespace,
            )
            ku_state = get_ku_state_template(name, namespace, extra_labels, existing_ku_state)
            logger.debug("generated updated KU State data", resourceName=name, kuStateData=str(cronjob))
            await k8s_crd.patch_namespaced_custom_object(
                name=name,
                group=KU_GROUP,
                version=KU_API_VERSION,
                plural=KU_STATE_PLURAL,
                namespace=namespace,
                body=ku_state,
                _content_type=MERGE_CONTENT_TYPE,
            )
            logger.info("patched KU State resource", resourceName=name)
        except Exception as ex:
            if isinstance(ex, kubernetes_asyncio.client.exceptions.ApiException) and ex.status == 404:
                logger.warn("KU State resource not found, attempting to create", resourceName=name)
                ku_state = get_ku_state_template(name, namespace, extra_labels)
                kopf.adopt(ku_state)
                logger.debug("created KU State data", resourceName=name, kuStateData=str(cronjob))
                await k8s_crd.create_namespaced_custom_object(
                    group=KU_GROUP,
                    version=KU_API_VERSION,
                    plural=KU_STATE_PLURAL,
                    namespace=namespace,
                    body=ku_state,
                    _content_type=CREATE_CONTENT_TYPE,
                )
                logger.info("created KU State resource", resourceName=name)
            else:
                raise

    except Exception as ex:
        log_unhandled_exceptions(
            ex,
            "PATCH",
            "update_ku_resources",
            "error updating KU resources",
            cronjob=str(cronjob),
            kuState=str(ku_state),
            crd=str(k8s_crd),
        )
        await _cleanup_resources(name, namespace)

        raise

    logger.debug("update complete", resourceName=name)


@kopf.on.startup()  # type: ignore[arg-type]
def configure(settings: kopf.OperatorSettings, **_):
    # Default worker limit is unbounded, which means it's possible to flood the API server on restart
    settings.batching.worker_limit = WORKER_LIMIT
    # Allow workers enough time to process large batches
    settings.batching.batch_window = 30
    settings.batching.exit_timeout = 10
    # All logs go to the Kubernetes Events API by default, making API server flooding more likely
    settings.posting.enabled = False
    # Timeouts prevent the worker from silently hanging when the connection pool is exhausted
    settings.networking.request_timeout = 60
    settings.networking.connect_timeout = 60
    settings.watching.connect_timeout = 60
    settings.watching.server_timeout = 60
    settings.watching.client_timeout = 60


# Serve prometheus metrics
start_http_server(SETTINGS.metrics_port)
