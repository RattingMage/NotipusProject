from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from ninja import Router
import requests

from .models import UserProfile, Organization
from .stripe_service import StripeService

auth_router = Router()


@auth_router.get("/slack/", auth=None)
def slack_auth(request):
    auth_url = f"https://slack.com/openid/connect/authorize?client_id={settings.SLACK_CLIENT_ID}&scope=openid%20email%20profile&redirect_uri={settings.SLACK_REDIRECT_URI}&response_type=code"
    return redirect(auth_url)


@auth_router.get("/slack/callback/", auth=None)
def slack_callback(request, code: str):
    response = requests.post('https://slack.com/api/openid.connect.token', data={
        'client_id': settings.SLACK_CLIENT_ID,
        'client_secret': settings.SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.SLACK_REDIRECT_URI
    })
    data = response.json()
    if not data.get('ok'):
        return JsonResponse({'error': 'Authentication failed'}, status=400)

    user_info_response = requests.get('https://slack.com/api/openid.connect.userInfo',
                                      headers={"Authorization": f"{data.get('token_type')} {data.get('access_token')}"})
    user_info = user_info_response.json()
    if not user_info.get('ok'):
        return JsonResponse({'error': 'Get user info failed'}, status=400)

    slack_user_id = user_info.get('sub')
    email = user_info.get('email')
    slack_team_id = user_info.get('https://slack.com/team_id')
    slack_domain = user_info.get('https://slack.com/team_domain')
    name = user_info.get('name')

    try:
        user_profile = UserProfile.objects.get(slack_user_id=slack_user_id)
        user = user_profile.user
    except UserProfile.DoesNotExist:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(username=name, email=email)
            user.set_unusable_password()
            user.save()

        try:
            organization = Organization.objects.get(
                Q(slack_team_id=slack_team_id) | Q(slack_domain=slack_domain)
            )
        except Organization.DoesNotExist:
            organization = Organization.objects.create(
                slack_team_id=slack_team_id,
                slack_domain=slack_domain,
                name=name,
                trial_end=timezone.now() + timezone.timedelta(days=14),
                subscription_status='trialing',
                monthly_limit=100
            )
            StripeService.setup_integration(organization)

        user_profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'slack_user_id': slack_user_id,
                'slack_team_id': slack_team_id,
                'organization': organization
            }
        )
        if not created:
            user_profile.slack_user_id = slack_user_id
            user_profile.slack_team_id = slack_team_id
            user_profile.organization = organization
            user_profile.save()

    login(request, user)
    return JsonResponse({
        "slack_user_id": user_profile.slack_user_id,
        "email": user.email,
        "slack_team_id": user_profile.slack_team_id,
        "slack_domain": user_profile.organization.slack_team_id,
        "name": user.username,
    }, status=200)


@auth_router.get("/subscription/status/", auth=None)
def subscription_status(request):
    slack_team_id = request.GET.get('team_id')
    if not slack_team_id:
        return JsonResponse({"error": "team_id parameter is required"}, status=400)

    try:
        organization = Organization.objects.get(slack_team_id=slack_team_id)
        return JsonResponse({
            "status": organization.subscription_status,
            "plan": organization.plan,
            "trial_end": organization.trial_end,
            "is_trial_active": organization.is_trial_active(),
            "stripe_connected": bool(organization.stripe_customer_id)
        })
    except Organization.DoesNotExist:
        return JsonResponse({"error": "Organization not found"}, status=404)
