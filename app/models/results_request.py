from kubernetes_asyncio.client import CoreV1Api, V1Pod
from pydantic import Field

from app.common.client import API_CLIENT
from app.common.logs import log_exception
from app.config import SETTINGS
from app.models import KUNotFoundError
from app.models._base import KubeUpBase
from app.models.synthetics_custom_metrics import SyntheticCustomMetric


class ResultsRequest(KubeUpBase):
    """
    Request model for the POST /synthetics/results endpoint
    """

    pod_name: str | None = Field(None, description="Pod name (if null, will be retrieved with IP)", examples=[None])
    custom_metrics: list[SyntheticCustomMetric] = Field([], description="Custom metrics")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._job_name = None
        self._check_name = None

    def _get_pod_details(self, pod: V1Pod) -> None:
        """
        Set pod, job, and check names

        :param pod: Pod object
        """

        self.pod_name = pod.metadata.name
        self._job_name = pod.metadata.labels["job-name"]
        self._check_name = pod.metadata.labels["kube-up.pitchbook.com/owning-cronjob"]
        try:
            self._timeout = int(pod.metadata.labels["kube-up.pitchbook.com/timeout"])
        except TypeError:
            self._timeout = None

    async def get_pod_details_from_name(self) -> None:
        """
        Set the pod, job, and check names from a pod IP
        """

        k8s_core = CoreV1Api(API_CLIENT.client)

        try:
            pod = await k8s_core.read_namespaced_pod(name=self.pod_name or "", namespace=SETTINGS.namespace)
            self._get_pod_details(pod)
        except Exception as ex:
            log_exception(ex, "Pod not found", podName=self.pod_name)
            raise KUNotFoundError(f"Pod '{self.pod_name}' not found") from ex

    async def get_pod_details_from_ip(self, ip: str) -> None:
        """
        Set the pod, job, and check names from a pod IP

        :param ip: Pod IP
        """

        k8s_core = CoreV1Api(API_CLIENT.client)

        try:
            # Select the most recent pod in case there are old pods with the same IP
            pod = sorted(
                (
                    await k8s_core.list_namespaced_pod(
                        namespace=SETTINGS.namespace, field_selector=f"status.podIP={ip}"
                    )
                ).items,
                key=lambda item: item.metadata.creation_timestamp,
                reverse=True,
            )[0]
            self._get_pod_details(pod)
        except IndexError as ex:
            log_exception(ex, "Pod not found", podIp=ip)
            raise KUNotFoundError(f"Pod IP '{ip}' not found") from ex

    @property
    def job_name(self) -> str | None:
        """
        Retrieve the job name

        :return: job name
        """

        return self._job_name

    @property
    def check_name(self) -> str | None:
        """
        Retrieve the KU Check name

        :return: KU Check name
        """

        return self._check_name

    @property
    def timeout(self):
        """
        Retrieve the KU Check timeout value

        :return: KU Check timeout value
        """

        return self._timeout

    def has_timed_out(self, run_duration: int) -> bool:
        """
        Check whether a run has timed out based on the run duration and specified timeout value

        :param run_duration: duration of job in seconds
        :return: whether or not job timed out (True means failure)
        """

        if not self._timeout:
            return False
        return run_duration > self._timeout
