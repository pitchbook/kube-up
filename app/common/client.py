import os

import kubernetes_asyncio
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.configuration import Configuration


class ApiSingleton:
    """
    Utility class to work around slow Configuration deepcopies
    see https://github.com/tomplus/kubernetes_asyncio/issues/247 for more details
    """

    config: Configuration
    client: ApiClient

    async def load(self):
        self.config = Configuration.get_default_copy()
        # Workaround for Python 3.13 SSL change
        self.config.disable_strict_ssl_verification = True
        self.client = ApiClient(self.config)


API_CLIENT = ApiSingleton()


async def init_api_client(**kwargs) -> str:
    """
    Load Kubernetes config and API client

    :return: The type of config loaded ("in-cluster" or "local")
    """

    # Startup
    if "KUBERNETES_PORT" in os.environ:
        config_type = "in-cluster"
        kubernetes_asyncio.config.load_incluster_config()
    else:
        config_type = "local"
        await kubernetes_asyncio.config.load_kube_config()
    await API_CLIENT.load()

    return config_type
