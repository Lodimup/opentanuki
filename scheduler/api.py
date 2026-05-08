from ninja import NinjaAPI
from ninja.security import django_auth

from .routes.dashboard import router as dashboard_router
from .routes.tasks import router as tasks_router

api = NinjaAPI(urls_namespace="scheduler-api", auth=django_auth)
api.add_router("/dashboard", dashboard_router)
api.add_router("/tasks", tasks_router)
