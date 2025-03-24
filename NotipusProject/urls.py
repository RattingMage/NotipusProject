"""
URL configuration for NotipusProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from ninja import NinjaAPI

from slack_auth.api import auth_router
from slack_auth.integration_api import integration_router
from webhook.api import webhook_router

api = NinjaAPI(
    title="Slack Auth API",
    version="1.0",
    description="API for Slack authentication and integrations management",
    csrf=True
)

api.add_router("/auth", auth_router, tags=["Authentication"])
api.add_router("/integration", integration_router, tags=["Integrations"])
api.add_router("/webhook", webhook_router, tags=["Webhooks"])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path(
        'stripe/success/',
        lambda request: JsonResponse({"status": "payment successful"}),
        name='stripe_success'
    ),
    path(
        'stripe/cancel/',
        lambda request: JsonResponse({"status": "payment cancelled"}),
        name='stripe_cancel'
    ),
]
