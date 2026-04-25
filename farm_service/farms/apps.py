import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FarmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'farms'

    # Consul registration handled by consul-registrar container only.