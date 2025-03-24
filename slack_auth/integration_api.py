from ninja import Router
from django.http import JsonResponse
from ninja.security import django_auth
from django.shortcuts import get_object_or_404

from .models import Integration
from .stripe_service import StripeService

integration_router = Router()


@integration_router.post("/stripe/connect/", auth=django_auth)
def connect_stripe(request):
    try:
        user_profile = request.user.userprofile
        organization = user_profile.organization

        checkout_url = StripeService.create_checkout_session(organization)

        return JsonResponse({
            "status": "success",
            "redirect_url": checkout_url,
            "organization_id": organization.id
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=400)


@integration_router.get("/stripe/status/", auth=django_auth)
def stripe_status(request):
    try:
        user_profile = request.user.userprofile
        organization = user_profile.organization

        integration = get_object_or_404(
            Integration,
            organization=organization,
            integration_type='stripe'
        )

        return {
            "connected": bool(organization.stripe_customer_id),
            "status": organization.subscription_status,
            "customer_id": organization.stripe_customer_id,
            "is_active": integration.is_active,
            "subscription_id": organization.stripe_subscription_id,
            "plan": organization.plan,
            "trial_end": organization.trial_end
        }

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=400)
