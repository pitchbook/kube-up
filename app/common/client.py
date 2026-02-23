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
