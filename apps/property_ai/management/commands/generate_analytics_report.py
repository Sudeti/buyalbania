from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Q
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.analytics import PropertyAnalytics
from datetime import datetime, timedelta
import json

class Command(BaseCommand):
    help = 'Generate comprehensive analytics report for market insights'
    
    def add_arguments(self, parser):
        parser.add_argument('--location', type=str, help='Specific location to analyze')
        parser.add_argument('--property-type', type=str, help='Specific property type to analyze')
        parser.add_argument('--months', type=int, default=6, help='Number of months to analyze')
        parser.add_argument('--export-json', action='store_true', help='Export report as JSON file')
    
    def handle(self, *args, **options):
        self.stdout.write("📊 GENERATING COMPREHENSIVE ANALYTICS REPORT")
        self.stdout.write("=" * 60)
        
        analytics = PropertyAnalytics()
        location = options['location']
        property_type = options['property_type']
        months = options['months']
        
        # Overall market summary
        self.stdout.write("\n🏠 OVERALL MARKET SUMMARY")
        self.stdout.write("-" * 30)
        
        market_summary = analytics.get_market_summary(location)
        if market_summary.get('market_stats'):
            stats = market_summary['market_stats']
            self.stdout.write(f"Total Properties Analyzed: {stats.get('total_properties', 0):,}")
            avg_price = stats.get('avg_price', 0) or 0
            self.stdout.write(f"Average Price: €{avg_price:,.0f}")
            avg_score = stats.get('avg_investment_score', 0) or 0
            self.stdout.write(f"Average Investment Score: {avg_score:.1f}")
            high_score_rate = stats.get('high_score_rate', 0) or 0
            self.stdout.write(f"High Score Rate: {high_score_rate:.1f}%")
            strong_buy_rate = stats.get('strong_buy_rate', 0) or 0
            self.stdout.write(f"Strong Buy Rate: {strong_buy_rate:.1f}%")
        
        # Location-specific analysis
        if location:
            self.stdout.write(f"\n📍 LOCATION ANALYSIS: {location}")
            self.stdout.write("-" * 40)
            
            location_stats = analytics.get_location_market_stats(location, property_type)
            if location_stats:
                self.stdout.write(f"Properties in {location}: {location_stats.get('total_properties', 0):,}")
                avg_price = location_stats.get('avg_price', 0) or 0
                self.stdout.write(f"Average Price: €{avg_price:,.0f}")
                min_price = location_stats.get('min_price', 0) or 0
                max_price = location_stats.get('max_price', 0) or 0
                self.stdout.write(f"Price Range: €{min_price:,.0f} - €{max_price:,.0f}")
                volatility = location_stats.get('price_volatility', 0) or 0
                self.stdout.write(f"Price Volatility: {volatility:.1f}%")
                self.stdout.write(f"Market Sentiment: {location_stats.get('market_sentiment', 'unknown')}")
                high_score_rate = location_stats.get('high_score_rate', 0) or 0
                self.stdout.write(f"High Score Rate: {high_score_rate:.1f}%")
                strong_buy_rate = location_stats.get('strong_buy_rate', 0) or 0
                self.stdout.write(f"Strong Buy Rate: {strong_buy_rate:.1f}%")
            
            # Price trends
            price_trends = analytics.get_price_trends(location, property_type, months)
            if price_trends:
                self.stdout.write(f"\n📈 PRICE TRENDS (Last {months} months)")
                self.stdout.write("-" * 35)
                for trend in price_trends[-3:]:  # Last 3 months
                    month = trend['month'].strftime('%B %Y')
                    avg_price = trend['avg_price']
                    avg_price_per_sqm = trend['avg_price_per_sqm']
                    count = trend['property_count']
                    self.stdout.write(f"{month}: €{avg_price:,.0f} avg | €{avg_price_per_sqm:,.0f}/m² | {count} properties")
        
        # Property type analysis
        if property_type:
            self.stdout.write(f"\n🏘️ PROPERTY TYPE ANALYSIS: {property_type}")
            self.stdout.write("-" * 45)
            
            type_stats = analytics.get_location_market_stats(location, property_type)
            if type_stats:
                self.stdout.write(f"Total {property_type} properties: {type_stats.get('total_properties', 0):,}")
                self.stdout.write(f"Average Price: €{type_stats.get('avg_price', 0):,.0f}")
                self.stdout.write(f"Average Price/m²: €{type_stats.get('avg_price_per_sqm', 0):,.0f}")
                self.stdout.write(f"Market Sentiment: {type_stats.get('market_sentiment', 'unknown')}")
        
        # Investment opportunity analysis
        self.stdout.write(f"\n💡 INVESTMENT OPPORTUNITY ANALYSIS")
        self.stdout.write("-" * 40)
        
        # Get recent high-opportunity properties
        recent_analyses = PropertyAnalysis.objects.filter(
            status='completed',
            market_opportunity_score__isnull=False
        ).order_by('-market_opportunity_score')[:10]
        
        if recent_analyses.exists():
            self.stdout.write("Top 10 High-Opportunity Properties:")
            for i, analysis in enumerate(recent_analyses, 1):
                opportunity_score = analysis.market_opportunity_score or 0
                price_position = analysis.market_position_percentage or 0
                leverage = analysis.negotiation_leverage or 'unknown'
                
                self.stdout.write(f"{i:2d}. {analysis.property_title[:40]}...")
                self.stdout.write(f"    Location: {analysis.property_location}")
                self.stdout.write(f"    Price: €{analysis.asking_price:,.0f} | Opportunity: {opportunity_score:.1f}")
                self.stdout.write(f"    Market Position: {price_position:+.1f}% | Leverage: {leverage}")
                self.stdout.write()
        
        # Market insights and recommendations
        self.stdout.write(f"\n🎯 MARKET INSIGHTS & RECOMMENDATIONS")
        self.stdout.write("-" * 45)
        
        # Analyze market conditions
        if market_summary.get('market_stats'):
            avg_score = market_summary['market_stats'].get('avg_investment_score', 0)
            high_score_rate = market_summary['market_stats'].get('high_score_rate', 0)
            
            if avg_score >= 75:
                self.stdout.write("✅ Market shows strong investment opportunities")
                self.stdout.write("   - High average investment scores indicate good market conditions")
                self.stdout.write("   - Consider increasing investment activity")
            elif avg_score >= 60:
                self.stdout.write("⚠️ Market shows moderate investment opportunities")
                self.stdout.write("   - Mixed market conditions, selective investing recommended")
                self.stdout.write("   - Focus on properties with high opportunity scores")
            else:
                self.stdout.write("❌ Market shows limited investment opportunities")
                self.stdout.write("   - Low average scores suggest challenging market conditions")
                self.stdout.write("   - Consider waiting for better opportunities or diversifying")
            
            if high_score_rate >= 30:
                self.stdout.write(f"✅ High-quality opportunities available ({high_score_rate:.1f}% high-score properties)")
            else:
                self.stdout.write(f"⚠️ Limited high-quality opportunities ({high_score_rate:.1f}% high-score properties)")
        
        # Export JSON report if requested
        if options['export_json']:
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'analysis_period': f"{months} months",
                'location': location,
                'property_type': property_type,
                'market_summary': market_summary,
                'location_analysis': location_stats if location else None,
                'top_opportunities': list(recent_analyses.values(
                    'property_title', 'property_location', 'asking_price',
                    'market_opportunity_score', 'market_position_percentage',
                    'negotiation_leverage', 'investment_score'
                )[:10])
            }
            
            filename = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.stdout.write(f"\n📄 Report exported to: {filename}")
        
        self.stdout.write(f"\n✅ Analytics report completed!")
        self.stdout.write(f"Analysis period: Last {months} months")
        if location:
            self.stdout.write(f"Location focus: {location}")
        if property_type:
            self.stdout.write(f"Property type focus: {property_type}")
