# apps/property_ai/management/commands/test_admin_views.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.property_ai.models import PropertyAnalysis
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Test admin views functionality'
    
    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Admin Views")
        
        # Check if we have a superuser
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            self.stdout.write(self.style.ERROR("❌ No superuser found. Please create one first."))
            return
        
        superuser = superusers.first()
        self.stdout.write(f"✅ Found superuser: {superuser.username}")
        
        # Check if we have property data
        properties = PropertyAnalysis.objects.filter(agent_name__isnull=False).exclude(agent_name='')
        if not properties.exists():
            self.stdout.write(self.style.WARNING("⚠️  No properties with agent data found. Creating test data..."))
            self.create_test_data()
            properties = PropertyAnalysis.objects.filter(agent_name__isnull=False).exclude(agent_name='')
        
        self.stdout.write(f"✅ Found {properties.count()} properties with agent data")
        
        # Test agent analytics view
        self.test_agent_analytics(superuser)
        
        # Test property rankings view
        self.test_property_rankings(superuser)
        
        self.stdout.write(self.style.SUCCESS("✅ All admin view tests completed!"))
    
    def create_test_data(self):
        """Create some test property data with agents"""
        test_agents = [
            {'name': 'John Smith', 'email': 'john@century21.com', 'phone': '+355676123456'},
            {'name': 'Maria Garcia', 'email': 'maria@century21.com', 'phone': '+355676789012'},
            {'name': 'Ahmet Yilmaz', 'email': 'ahmet@century21.com', 'phone': '+355676345678'},
        ]
        
        locations = ['Tirana, Albania', 'Durrës, Albania', 'Vlorë, Albania']
        neighborhoods = ['Blloku', 'Qendra', 'Kombinat', 'Astir']
        property_types = ['apartment', 'villa', 'commercial']
        
        for i, agent in enumerate(test_agents):
            for j in range(5):  # Create 5 properties per agent for better variance
                # Vary prices more to test difficulty coefficient
                base_price = 120000 + (i * 30000) + (j * 15000)
                price_variation = (j % 3 - 1) * 20000  # -20k, 0, +20k
                asking_price = Decimal(str(base_price + price_variation))
                
                # Vary areas
                total_area = 75 + (i * 15) + (j * 8)
                internal_area = 65 + (i * 12) + (j * 6)
                
                # Vary investment scores
                investment_score = 65 + (i * 8) + (j * 3)
                if investment_score > 100:
                    investment_score = 100
                
                PropertyAnalysis.objects.create(
                    property_url=f"https://test{i}{j}.com",
                    property_title=f"Test Property {i}{j} - {locations[i % len(locations)]}",
                    property_location=locations[i % len(locations)],
                    neighborhood=neighborhoods[j % len(neighborhoods)],
                    asking_price=asking_price,
                    property_type=property_types[j % len(property_types)],
                    total_area=total_area,
                    internal_area=internal_area,
                    bedrooms=1 + (j % 3),
                    investment_score=investment_score,
                    recommendation='strong_buy' if investment_score >= 80 else 'buy' if investment_score >= 70 else 'hold',
                    market_opportunity_score=Decimal('75.5') + (i * 2.5) + (j * 1.5),
                    price_percentile=Decimal('60.0') + (i * 5.0) + (j * 2.0),
                    market_position_percentage=Decimal('-5.0') + (i * 2.0) + (j * 1.0),
                    negotiation_leverage='high' if j % 3 == 0 else 'medium' if j % 3 == 1 else 'low',
                    market_sentiment='bullish' if i % 2 == 0 else 'neutral',
                    agent_name=agent['name'],
                    agent_email=agent['email'],
                    agent_phone=agent['phone'],
                    status='completed',
                    is_active=True
                )
        
        self.stdout.write("✅ Created test property data with agents")
    
    def test_agent_analytics(self, superuser):
        """Test agent analytics view"""
        self.stdout.write("🔍 Testing Agent Analytics View...")
        
        client = Client()
        client.force_login(superuser)
        
        try:
            response = client.get(reverse('property_ai:admin_agent_analytics'))
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("✅ Agent analytics view works"))
                
                # Simple context check
                if hasattr(response, 'context') and response.context:
                    self.stdout.write(f"   📊 Context keys: {list(response.context.keys())}")
                    if 'agents' in response.context:
                        agents = response.context['agents']
                        if agents:
                            self.stdout.write(f"   📊 Found {len(agents)} agents")
                            if len(agents) > 0:
                                top_agent = agents[0]
                                self.stdout.write(f"   🏆 Top agent: {top_agent.get('agent_name', 'N/A')}")
                                self.stdout.write(f"   📈 Difficulty: {top_agent.get('difficulty_coefficient', 'N/A')}")
                        else:
                            self.stdout.write("   ⚠️  No agents in context")
                    else:
                        self.stdout.write("   ⚠️  'agents' not in context")
                else:
                    self.stdout.write("   ⚠️  No context available")
            else:
                self.stdout.write(self.style.ERROR(f"❌ Agent analytics view failed: {response.status_code}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Agent analytics view error: {e}"))
    
    def test_property_rankings(self, superuser):
        """Test property rankings view"""
        self.stdout.write("🔍 Testing Property Rankings View...")
        
        client = Client()
        client.force_login(superuser)
        
        try:
            response = client.get(reverse('property_ai:admin_property_rankings'))
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("✅ Property rankings view works"))
                
                # Check if we have property data in the response
                try:
                    if 'properties' in response.context and response.context['properties'] is not None:
                        properties_data = response.context['properties']
                        if hasattr(properties_data, '__iter__') and not isinstance(properties_data, str):
                            properties_count = len(properties_data)
                            self.stdout.write(f"   📊 Found {properties_count} properties in rankings")
                            
                            # Show some property details
                            if properties_count > 0:
                                top_property = properties_data[0]
                                self.stdout.write(f"   🏆 Top property: {top_property.get('title', 'N/A')[:30]}... (Rank: {top_property.get('rank', 'N/A')})")
                                if 'price_per_sqm' in top_property:
                                    self.stdout.write(f"   💰 Price per m²: €{top_property.get('price_per_sqm', 'N/A')}")
                        else:
                            self.stdout.write(self.style.WARNING("   ⚠️  Properties data is not iterable"))
                    else:
                        self.stdout.write(self.style.WARNING("   ⚠️  No properties data in context"))
                except Exception as context_error:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Context error: {context_error}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Property rankings view failed: {response.status_code}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Property rankings view error: {e}"))
