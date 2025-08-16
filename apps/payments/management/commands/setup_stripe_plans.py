from django.core.management.base import BaseCommand
from apps.payments.models import SubscriptionPlan
import stripe
from django.conf import settings

class Command(BaseCommand):
    help = 'Set up Stripe subscription plans'

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        # Define plans
        plans_data = [
            {
                'tier': 'free',
                'name': 'Free',
                'price_monthly': 0,
                'analyses_per_month': 1,
                'features': [
                    '1 property analysis per month',
                    'AI investment score',
                    'PDF report via email',
                    'Access to existing analyses',
                    'No market insights',
                ]
            },
            {
                'tier': 'basic',
                'name': 'Basic',
                'price_monthly': 19.00,
                'analyses_per_month': 10,
                'features': [
                    '10 property analyses per month',
                    'AI investment score & recommendations',
                    'PDF reports via email',
                    'Property deal alerts',
                    'Enhanced market analytics',
                    'Negotiation leverage insights',
                    'Access to all existing analyses',
                    'Priority email support',
                ]
            },
            {
                'tier': 'premium',
                'name': 'Premium',
                'price_monthly': 49.00,
                'analyses_per_month': -1,  # Unlimited
                'features': [
                    'Unlimited property analyses',
                    'AI investment score & recommendations',
                    'PDF reports via email',
                    'Advanced property alerts',
                    'Comprehensive market analytics',
                    'Portfolio analytics dashboard',
                    'My analyses tracking',
                    'Priority customer support',
                    'Market trend analysis',
                    'ROI projections',
                ]
            }
        ]
        
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                tier=plan_data['tier'],
                defaults={
                    'name': plan_data['name'],
                    'price_monthly': plan_data['price_monthly'],
                    'analyses_per_month': plan_data['analyses_per_month'],
                    'features': plan_data['features'],
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
                
                # Create Stripe product and price for paid plans
                if plan.price_monthly > 0:
                    try:
                        # Create Stripe product
                        product = stripe.Product.create(
                            name=plan.name,
                            description=f"PropertyAI {plan.name} Plan",
                            metadata={'plan_tier': plan.tier}
                        )
                        
                        # Create Stripe price
                        price = stripe.Price.create(
                            product=product.id,
                            unit_amount=int(plan.price_monthly * 100),  # Convert to cents
                            currency='eur',
                            recurring={'interval': 'month'},
                            metadata={'plan_tier': plan.tier}
                        )
                        
                        # Update plan with Stripe IDs
                        plan.stripe_price_id_monthly = price.id
                        plan.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'Created Stripe product and price for {plan.name}')
                        )
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error creating Stripe product for {plan.name}: {e}')
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Plan already exists: {plan.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up subscription plans')
        )
