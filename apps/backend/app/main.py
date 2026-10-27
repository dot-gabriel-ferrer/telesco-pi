"""Environment-configured ASGI entrypoint for managed deployments."""

from apps.backend.app.factory import create_app

app = create_app()
