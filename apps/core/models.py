# apps/core/models.py
from django.db import models

class TimeStampedModel(models.Model):
    """Base model with created and updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class SingletonModel(models.Model):
    """Base model for singleton patterns (e.g., site settings)"""
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class SiteSettings(SingletonModel, TimeStampedModel):
    """Global site settings"""
    site_name = models.CharField(max_length=255, default="My Site")
    maintenance_mode = models.BooleanField(default=False)
    max_free_usages = models.IntegerField(default=3)
    premium_price = models.DecimalField(max_digits=6, decimal_places=2, default=5.99)
    
    def __str__(self):
        return f"Site Settings"