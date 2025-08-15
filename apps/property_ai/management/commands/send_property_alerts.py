from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.property_ai.tasks import send_property_alerts_task, send_property_alert_email
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.analytics import PropertyAnalytics
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Manually trigger property alerts for testing or debugging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Send alerts only to a specific user ID',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=1,
            help='Look for properties added in the last N days (default: 1)',
        )
        parser.add_argument(
            '--min-discount',
            type=float,
            default=10.0,
            help='Minimum price discount percentage (default: 10.0)',
        )
        parser.add_argument(
            '--test-email',
            action='store_true',
            help='Send a test email to the first user with alerts enabled',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options['user_id']
        days_back = options['days_back']
        min_discount = options['min_discount']
        test_email = options['test_email']

        self.stdout.write(
            self.style.SUCCESS(f'🚀 Property Alerts Command')
        )
        self.stdout.write(f'   Dry run: {dry_run}')
        self.stdout.write(f'   Days back: {days_back}')
        self.stdout.write(f'   Min discount: {min_discount}%')
        self.stdout.write('')

        if test_email:
            self.test_email_sending()
            return

        if user_id:
            self.send_alerts_to_user(user_id, dry_run, days_back, min_discount)
        else:
            self.send_alerts_to_all_users(dry_run, days_back, min_discount)

    def test_email_sending(self):
        """Send a test email to verify the system works"""
        self.stdout.write('📧 Testing Email Sending...')
        
        # Get first user with alerts enabled
        user = User.objects.filter(
            profile__email_property_alerts=True,
            profile__is_email_verified=True,
            is_active=True
        ).first()
        
        if not user:
            self.stdout.write(
                self.style.ERROR('❌ No users with property alerts enabled found')
            )
            return
        
        # Get some test properties
        properties = PropertyAnalysis.objects.filter(
            status='completed',
            investment_score__gte=70
        )[:3]
        
        if not properties.exists():
            self.stdout.write(
                self.style.ERROR('❌ No test properties available')
            )
            return
        
        property_ids = [p.id for p in properties]
        
        self.stdout.write(f'   👤 Test user: {user.email}')
        self.stdout.write(f'   🏠 Properties: {properties.count()}')
        
        try:
            result = send_property_alert_email.delay(user.id, property_ids)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Test email queued: {result.id}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Test email failed: {e}')
            )

    def send_alerts_to_user(self, user_id, dry_run, days_back, min_discount):
        """Send alerts to a specific user"""
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f'👤 Sending alerts to user: {user.email}')
            
            if not user.profile.email_property_alerts:
                self.stdout.write(
                    self.style.WARNING('⚠️  User has property alerts disabled')
                )
                return
            
            good_deals = self.find_good_deals(days_back, min_discount)
            user_deals = self.filter_deals_for_user(good_deals, user)
            
            if not user_deals:
                self.stdout.write('   📭 No matching properties for this user')
                return
            
            self.stdout.write(f'   🏠 Found {len(user_deals)} matching properties')
            
            if not dry_run:
                property_ids = [deal['property'].id for deal in user_deals]
                result = send_property_alert_email.delay(user.id, property_ids)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Alert email queued: {result.id}')
                )
            else:
                self.stdout.write('   🔍 Dry run - no email sent')
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User with ID {user_id} not found')
            )

    def send_alerts_to_all_users(self, dry_run, days_back, min_discount):
        """Send alerts to all eligible users"""
        self.stdout.write('👥 Processing alerts for all users...')
        
        # Get users who want alerts
        users_with_alerts = User.objects.filter(
            profile__email_property_alerts=True,
            profile__is_email_verified=True,
            is_active=True
        ).select_related('profile')
        
        if not users_with_alerts.exists():
            self.stdout.write(
                self.style.WARNING('⚠️  No users with property alerts enabled')
            )
            return
        
        self.stdout.write(f'   👥 Found {users_with_alerts.count()} users with alerts enabled')
        
        # Find good deals
        good_deals = self.find_good_deals(days_back, min_discount)
        
        if not good_deals:
            self.stdout.write('   📭 No good deals found')
            return
        
        self.stdout.write(f'   🏠 Found {len(good_deals)} good deals')
        
        # Process each user
        alerts_sent = 0
        for user in users_with_alerts:
            user_deals = self.filter_deals_for_user(good_deals, user)
            
            if user_deals:
                self.stdout.write(f'   👤 {user.email}: {len(user_deals)} properties')
                
                if not dry_run:
                    property_ids = [deal['property'].id for deal in user_deals]
                    send_property_alert_email.delay(user.id, property_ids)
                    alerts_sent += 1
            else:
                self.stdout.write(f'   👤 {user.email}: No matching properties')
        
        if dry_run:
            self.stdout.write(f'🔍 Dry run complete - would send {alerts_sent} alerts')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sent {alerts_sent} property alerts')
            )

    def find_good_deals(self, days_back, min_discount):
        """Find properties that are good deals"""
        # Get properties from specified time period
        start_date = timezone.now() - timedelta(days=days_back)
        new_properties = PropertyAnalysis.objects.filter(
            created_at__gte=start_date,
            status='completed',
            scraped_by__isnull=False,
            user__isnull=True
        )
        
        if not new_properties.exists():
            return []
        
        # Group by location
        properties_by_location = {}
        for prop in new_properties:
            location = prop.property_location.split(',')[0].strip()
            if location not in properties_by_location:
                properties_by_location[location] = []
            properties_by_location[location].append(prop)
        
        # Find good deals
        analytics = PropertyAnalytics()
        good_deals = []
        
        for location, properties in properties_by_location.items():
            market_stats = analytics.get_location_market_stats(location)
            if market_stats and market_stats.get('avg_price'):
                avg_price = market_stats['avg_price']
                for prop in properties:
                    if prop.asking_price and avg_price:
                        price_discount = ((avg_price - prop.asking_price) / avg_price) * 100
                        if price_discount >= min_discount:
                            good_deals.append({
                                'property': prop,
                                'location': location,
                                'price_discount': price_discount,
                                'market_stats': market_stats
                            })
        
        return good_deals

    def filter_deals_for_user(self, good_deals, user):
        """Filter deals based on user preferences"""
        user_deals = []
        for deal in good_deals:
            if user.profile.should_receive_property_alert(deal['property']):
                user_deals.append(deal)
        return user_deals
