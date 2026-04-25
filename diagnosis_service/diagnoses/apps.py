import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DiagnosesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'diagnoses'

    # Consul registration handled by consul-registrar container only.