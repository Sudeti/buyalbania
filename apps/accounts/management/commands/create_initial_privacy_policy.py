from django.core.management.base import BaseCommand
from apps.accounts.models import PrivacyPolicyVersion
from django.utils import timezone

class Command(BaseCommand):
    help = 'Creates the initial privacy policy version'

    def handle(self, *args, **options):
        # Check if any policy already exists
        if PrivacyPolicyVersion.objects.exists():
            self.stdout.write(self.style.WARNING('Privacy policy already exists. Skipping creation.'))
            return
        
        # Create the initial policy
        with open('apps/accounts/templates/accounts/privacy_policy_content.html', 'r') as file:
            policy_content = file.read()
        
        PrivacyPolicyVersion.objects.create(
            version="1.0",
            content=policy_content,
            effective_date=timezone.now().date(),
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully created initial privacy policy version 1.0'))