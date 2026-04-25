from django.apps import AppConfig


class GatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gateway'

    # Consul registration is handled exclusively by the consul-registrar
    # container (consul_registrar/registrar.py), which re-registers every 60s.
    # DO NOT register here — apps.py ready() runs twice in dev mode (autoreloader)
    # and races with the registrar container, causing intermittent 404s on Traefik.