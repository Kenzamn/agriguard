from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    # Consul registration handled by consul-registrar container only.
    # Self-registration in ready() causes race conditions with the
    # autoreloader (ready() fires twice) and the registrar container.