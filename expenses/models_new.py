from django.db import models

# ... existing code ...

class SubscriptionPlan(models.Model):
    TIER_CHOICES = [
        ('PLUS', 'Plus'),
        ('PRO', 'Pro'),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in INR")
    features = models.TextField(help_text="Comma separated features", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"
