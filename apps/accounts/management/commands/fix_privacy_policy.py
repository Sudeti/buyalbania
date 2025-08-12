from django.core.management.base import BaseCommand
from apps.accounts.models import PrivacyPolicyVersion
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Fixes the privacy policy content in the database'

    def handle(self, *args, **options):
        # Correct content path
        content_path = os.path.join(
            settings.BASE_DIR,
            'apps/accounts/templates/accounts/privacy_policy_content.html'
        )
        
        # Check if the file exists first
        if not os.path.exists(content_path):
            self.stdout.write(self.style.ERROR(f"Content file not found at {content_path}"))
            return
        
        # Read the correct content
        with open(content_path, 'r') as file:
            correct_content = file.read()
        
        # Update all policy versions
        versions = PrivacyPolicyVersion.objects.all()
        
        if not versions.exists():
            self.stdout.write(self.style.WARNING("No privacy policy versions found in database"))
            return
        
        for version in versions:
            version.content = correct_content
            version.save()
            self.stdout.write(self.style.SUCCESS(f"Updated content for policy version {version.version}"))