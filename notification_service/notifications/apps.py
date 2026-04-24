import logging
import os
import requests
from django.apps import AppConfig

logger = logging.getLogger(__name__)

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        self._register_consul()

    def _register_consul(self):
        consul_host = os.environ.get('CONSUL_HOST', 'consul')
        service_host = os.environ.get('HOSTNAME', 'agriguard-notification')
        payload = {
            "ID":      "notification-service-1",
            "Name":    "notification-service",
            "Address": service_host,
            "Port":    8004,
            "Tags": [
                "traefik.enable=true",
                "traefik.http.routers.notify.rule=PathPrefix(`/api/notify`)",
                "traefik.http.routers.notify.entrypoints=web",
                "traefik.http.routers.notify.priority=100",
            ],
            "Check": {
                "HTTP":     f"http://{service_host}:8004/api/notify/health/",
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
                logger.info("Notification Service registered with Consul")
            else:
                logger.warning(f"Consul registration failed: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"Could not reach Consul: {e}")
