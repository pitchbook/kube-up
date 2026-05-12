from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.logs import setup_logging


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    log_level: str = Field("info")
    host_address: str = Field("0.0.0.0")
    host_port: int = Field(8080)
    metrics_port: int = Field(8000)
    timeout: int = Field(300)
    namespace: str = Field("kube-up")
    ku_group: str = Field("pitchbook.com")
    ku_api_version: str = Field("v1")
    ku_state_plural: str = Field("kustates")
    extra_metrics_labels: list[str] = Field([])
    api_service_name: str = Field("kube-up-api")
    api_url_env_var: str = Field("KU_API_URL")


SETTINGS = Settings()

setup_logging(SETTINGS.log_level, {"aiohttp": "warning", "kopf": "warning"})

ALL_METRICS_LABELS = (
    "name",
    "namespace",
    *SETTINGS.extra_metrics_labels,
)
