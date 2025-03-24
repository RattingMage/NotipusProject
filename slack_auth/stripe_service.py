import stripe
from django.conf import settings
from django.utils import timezone
from .models import Organization, Integration

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    @staticmethod
    def setup_integration(organization):
        integration, created = Integration.objects.get_or_create(
            organization=organization,
            integration_type='stripe',
            defaults={
                'auth_data': {},
                'is_active': True
            }
        )

        if not integration.is_active:
            integration.is_active = True
            integration.save()

        if not organization.stripe_customer_id:
            customer_email = organization.get_primary_email()

            customer = stripe.Customer.create(
                email=customer_email,
                name=organization.name,
                metadata={
                    'slack_team_id': organization.slack_team_id,
                    'organization_id': organization.id,
                    'integration_id': integration.id
                }
            )

            organization.stripe_customer_id = customer.id
            organization.save()

            integration.auth_data = {
                'customer_id': customer.id,
                'created_at': timezone.now().isoformat(),
                'last_sync': timezone.now().isoformat()
            }
            integration.save()

        return integration

    @staticmethod
    def create_checkout_session(organization, price_id=settings.STRIPE_PRICE_ID):
        integration = StripeService.setup_integration(organization)

        session = stripe.checkout.Session.create(
            customer=organization.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={
                'organization_id': organization.id,
                'integration_id': integration.id
            },
            subscription_data={
                'trial_end': int(organization.trial_end.timestamp()) if organization.trial_end else None,
                'metadata': {
                    'organization_id': organization.id,
                    'integration_id': integration.id
                }
            }
        )

        integration.auth_data['checkout_session_id'] = session.id
        integration.save()

        return session.url

    @staticmethod
    def handle_webhook_event(event):
        event_type = event['type']
        data = event['data']['object']

        try:
            if event_type == 'checkout.session.completed':
                integration_id = data.metadata.get('integration_id')
                integration = Integration.objects.get(id=integration_id)

                integration.auth_data.update({
                    'checkout_completed': True,
                    'checkout_completed_at': timezone.now().isoformat(),
                    'session_id': data.id
                })
                integration.save()

            elif event_type in ['customer.subscription.created', 'customer.subscription.updated']:
                customer_id = data.customer
                organization = Organization.objects.get(stripe_customer_id=customer_id)
                integration = Integration.objects.get(
                    organization=organization,
                    integration_type='stripe'
                )

                organization.stripe_subscription_id = data.id
                organization.subscription_status = data.status
                organization.plan = data.plan.id if hasattr(data, 'plan') else 'free'
                organization.save()

                integration.auth_data.update({
                    'subscription_id': data.id,
                    'subscription_status': data.status,
                    'current_period_end': data.current_period_end,
                    'last_sync': timezone.now().isoformat()
                })
                integration.save()

                if data.status == 'active':
                    organization.monthly_limit = settings.PLAN_LIMITS.get('premium', 1000)
                    organization.save()

            elif event_type == 'invoice.payment_succeeded':
                customer_id = data.customer
                organization = Organization.objects.get(stripe_customer_id=customer_id)

                if hasattr(data, 'subscription'):
                    subscription = stripe.Subscription.retrieve(data.subscription)
                    integration = Integration.objects.get(
                        organization=organization,
                        integration_type='stripe'
                    )
                    integration.auth_data['current_period_end'] = subscription.current_period_end
                    integration.save()

            elif event_type == 'invoice.payment_failed':
                customer_id = data.customer
                organization = Organization.objects.get(stripe_customer_id=customer_id)
                organization.subscription_status = 'past_due'
                organization.save()

                integration = Integration.objects.get(
                    organization=organization,
                    integration_type='stripe'
                )
                integration.auth_data['payment_failed'] = True
                integration.auth_data['last_payment_failed_at'] = timezone.now().isoformat()
                integration.save()

        except (Organization.DoesNotExist, Integration.DoesNotExist) as e:
            print(f"Error processing Stripe webhook: {str(e)}")
            raise
