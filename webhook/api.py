from django.http import HttpResponse, JsonResponse
from django.conf import settings
from ninja import Router

import stripe
import logging

from slack_auth.stripe_service import StripeService

logger = logging.getLogger(__name__)
webhook_router = Router()


@webhook_router.post('/health_check/')
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({"status": "healthy"}, status=200)


@webhook_router.post('/stripe/')
def stripe_webhook(request):
    logger.info("Received Stripe webhook event")

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
        logger.debug(f"Stripe event type: {event['type']}, ID: {event.get('id')}")
    except ValueError as e:
        logger.error(f"Invalid Stripe payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid Stripe signature: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception("Unexpected error during Stripe event verification")
        return HttpResponse(status=400)

    try:
        StripeService.handle_webhook_event(event)
        logger.info(f"Successfully processed Stripe event: {event['type']}")
    except Exception as e:
        logger.error(f"Error processing Stripe webhook {event.get('id')}: {str(e)}",
                     exc_info=True)
        return HttpResponse(status=200)

    return HttpResponse(status=200)
