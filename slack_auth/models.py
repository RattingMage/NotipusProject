from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Organization(models.Model):
    slack_team_id = models.CharField(max_length=255, unique=True)
    slack_domain = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)

    # Stripe fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_status = models.CharField(max_length=20, default='inactive')
    trial_end = models.DateTimeField(null=True, blank=True)
    plan = models.CharField(max_length=20, default='free')

    # Usage tracking
    monthly_usage = models.PositiveIntegerField(default=0)
    monthly_limit = models.PositiveIntegerField(default=100)  # Default trial limit

    def is_trial_active(self):
        return self.subscription_status == 'trialing' and (
                self.trial_end is None or
                self.trial_end > timezone.now()
        )

    def has_active_subscription(self):
        return self.subscription_status in ['active', 'trialing']

    def check_usage(self, increment=0):
        if self.is_trial_active() or self.subscription_status == 'active':
            return (self.monthly_usage + increment) <= self.monthly_limit
        return False

    def increment_usage(self, amount=1):
        if self.check_usage(amount):
            self.monthly_usage += amount
            self.save()
            return True
        return False

    def get_primary_email(self):
        admin = self.userprofile_set.first()
        if admin:
            return admin.user.email
        return None


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=255, unique=True)
    slack_team_id = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)


class Integration(models.Model):
    INTEGRATION_TYPES = (
        ('stripe', 'Stripe'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='integrations')
    integration_type = models.CharField(max_length=50, choices=INTEGRATION_TYPES)
    auth_data = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'integration_type')
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'

    def __str__(self):
        return f"{self.get_integration_type_display()} for {self.organization.name}"