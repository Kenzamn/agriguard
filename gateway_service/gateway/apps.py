import logging
import os
import requests
from django.apps import AppConfig

logger = logging.getLogger(__name__)

class GatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gateway'

    def ready(self):
        self._register_consul()

    def _register_consul(self):
        consul_host = os.environ.get('CONSUL_HOST', 'consul')
        service_host = os.environ.get('HOSTNAME', 'agriguard-gateway')
        payload = {
            "ID":      "gateway-service-1",
            "Name":    "gateway-service",
            "Address": service_host,
            "Port":    8080,
            "Tags": [
                "traefik.enable=true",
                "traefik.http.routers.gateway.rule=PathPrefix(`/`)",
                "traefik.http.routers.gateway.entrypoints=web",
                "traefik.http.routers.gateway.priority=1",
            ],
            "Check": {
                "HTTP":     f"http://{service_host}:8080/health/",
                "Interval": "10s",
                "Timeout":  "3s",
            }
        }
        try:
            r = requests.put(
                f"http://{consul_host}:8500/v1/agent/service/register",
                json=payload,
                timeout=3,
            )
            if r.status_code == 200:
                logger.info("Gateway Service registered with Consul")
            else:
                logger.warning(f"Consul registration failed: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"Could not reach Consul: {e}")
