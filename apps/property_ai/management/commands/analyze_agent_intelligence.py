# apps/property_ai/management/commands/analyze_agent_intelligence.py
from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from apps.property_ai.models import PropertyAnalysis

class Command(BaseCommand):
    help = 'Analyze agent intelligence data for business insights'
    
    def add_arguments(self, parser):
        parser.add_argument('--export-contacts', action='store_true', 
                          help='Export agent contact list to CSV')
        parser.add_argument('--top-n', type=int, default=20,
                          help='Number of top agents to show')
    
    def handle(self, *args, **options):
        self.stdout.write("🕵️ AGENT INTELLIGENCE ANALYSIS")
        
        # Overall agent statistics
        total_properties = PropertyAnalysis.objects.count()
        
        with_agent_data = PropertyAnalysis.objects.filter(
            agent_name__isnull=False
        ).exclude(agent_name='')
        
        total_with_agents = with_agent_data.count()
        coverage_percentage = (total_with_agents / total_properties * 100) if total_properties > 0 else 0
        
        self.stdout.write(f"\n📊 OVERALL COVERAGE:")
        self.stdout.write(f"🏠 Total properties: {total_properties:,}")
        self.stdout.write(f"🧑‍💼 With agent data: {total_with_agents:,} ({coverage_percentage:.1f}%)")
        
        # Agent performance analysis
        agent_performance = with_agent_data.values('agent_name').annotate(
            total_listings=Count('id'),
            avg_price=Avg('asking_price'),
            avg_score=Avg('investment_score'),
            premium_listings=Count('id', filter=Q(asking_price__gte=200000)),
            high_score_listings=Count('id', filter=Q(investment_score__gte=80))
        ).order_by('-total_listings')[:options['top_n']]
        
        self.stdout.write(f"\n🏆 TOP {options['top_n']} AGENTS BY LISTINGS:")
        self.stdout.write(f"{'Rank':<4} {'Agent Name':<25} {'Listings':<8} {'Avg Price':<12} {'Premium':<8} {'High Score':<10}")
        self.stdout.write("-" * 75)
        
        for i, agent in enumerate(agent_performance, 1):
            avg_price = f"€{agent['avg_price']:,.0f}" if agent['avg_price'] else "N/A"
            self.stdout.write(
                f"{i:<4} {agent['agent_name'][:24]:<25} "
                f"{agent['total_listings']:<8} {avg_price:<12} "
                f"{agent['premium_listings']:<8} {agent['high_score_listings']:<10}"
            )
        
        # Contact information analysis
        contact_stats = PropertyAnalysis.objects.filter(
            agent_name__isnull=False
        ).exclude(agent_name='').aggregate(
            total_agents=Count('agent_name', distinct=True),
            with_email=Count('agent_email', filter=Q(agent_email__isnull=False)),
            with_phone=Count('agent_phone', filter=Q(agent_phone__isnull=False))
        )
        
        unique_agents = PropertyAnalysis.objects.filter(
            agent_name__isnull=False
        ).exclude(agent_name='').values('agent_name').distinct().count()
        
        unique_emails = PropertyAnalysis.objects.filter(
            agent_email__isnull=False
        ).exclude(agent_email='').values('agent_email').distinct().count()
        
        self.stdout.write(f"\n📧 CONTACT INFORMATION:")
        self.stdout.write(f"👥 Unique agents identified: {unique_agents}")
        self.stdout.write(f"📧 Unique email addresses: {unique_emails}")
        self.stdout.write(f"📞 Properties with phone numbers: {contact_stats['with_phone']}")
        
        # Territory analysis
        territory_analysis = with_agent_data.values('agent_name', 'property_location').annotate(
            count=Count('id')
        ).order_by('agent_name', '-count')
        
        # Group by agent to find territory concentration
        agent_territories = {}
        for item in territory_analysis:
            agent = item['agent_name']
            if agent not in agent_territories:
                agent_territories[agent] = []
            agent_territories[agent].append({
                'location': item['property_location'],
                'count': item['count']
            })
        
        # Find agents with territory concentration (>50% in one area)
        concentrated_agents = []
        for agent, territories in agent_territories.items():
            total_listings = sum(t['count'] for t in territories)
            if territories and territories[0]['count'] / total_listings > 0.5:
                concentrated_agents.append({
                    'agent': agent,
                    'primary_territory': territories[0]['location'],
                    'concentration': territories[0]['count'] / total_listings * 100,
                    'total_listings': total_listings
                })
        
        if concentrated_agents:
            concentrated_agents.sort(key=lambda x: x['total_listings'], reverse=True)
            self.stdout.write(f"\n🎯 AGENTS WITH TERRITORY CONCENTRATION (>50% in one area):")
            for agent_data in concentrated_agents[:10]:
                self.stdout.write(
                    f"  🧑‍💼 {agent_data['agent']}: {agent_data['concentration']:.1f}% in "
                    f"{agent_data['primary_territory']} ({agent_data['total_listings']} total)"
                )
        
        # Revenue potential
        self.calculate_revenue_potential(unique_emails)
        
        # Export contacts if requested
        if options['export_contacts']:
            self.export_agent_contacts()
    
    def calculate_revenue_potential(self, unique_emails):
        """Calculate potential revenue from agent intelligence services"""
        self.stdout.write(f"\n💰 REVENUE POTENTIAL ANALYSIS:")
        
        # Different tiers and conversion rates
        tiers = {
            'Basic Agent Intelligence': {'price': 299, 'conversion': 0.05},
            'Professional Agent Intelligence': {'price': 599, 'conversion': 0.03},
            'Ultimate Agent Intelligence': {'price': 1299, 'conversion': 0.01}
        }
        
        total_potential = 0
        for tier_name, tier_data in tiers.items():
            agents_converted = int(unique_emails * tier_data['conversion'])
            monthly_revenue = agents_converted * tier_data['price']
            annual_revenue = monthly_revenue * 12
            total_potential += monthly_revenue
            
            self.stdout.write(
                f"  📊 {tier_name}: {agents_converted} agents × €{tier_data['price']} = "
                f"€{monthly_revenue:,}/month (€{annual_revenue:,}/year)"
            )
        
        self.stdout.write(f"\n🎯 TOTAL MONTHLY POTENTIAL: €{total_potential:,}")
        self.stdout.write(f"🚀 TOTAL ANNUAL POTENTIAL: €{total_potential * 12:,}")
    
    def export_agent_contacts(self):
        """Export agent contact list to CSV"""
        import csv
        from datetime import datetime
        
        filename = f"agent_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        agents = PropertyAnalysis.objects.filter(
            agent_name__isnull=False,
            agent_email__isnull=False
        ).exclude(
            agent_name='',
            agent_email=''
        ).values('agent_name', 'agent_email', 'agent_phone').distinct()
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['agent_name', 'agent_email', 'agent_phone', 'total_listings']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for agent in agents:
                # Get listing count for each agent
                listing_count = PropertyAnalysis.objects.filter(
                    agent_name=agent['agent_name']
                ).count()
                
                writer.writerow({
                    'agent_name': agent['agent_name'],
                    'agent_email': agent['agent_email'],
                    'agent_phone': agent['agent_phone'] or '',
                    'total_listings': listing_count
                })
        
        self.stdout.write(f"📋 Agent contacts exported to: {filename}")