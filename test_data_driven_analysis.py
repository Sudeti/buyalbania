#!/usr/bin/env python
"""
Test script for data-driven property analysis
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.data_driven_analyzer import DataDrivenAnalyzer
from decimal import Decimal

def test_data_driven_analysis():
    """Test the data-driven analysis system"""
    print("🧪 Testing Data-Driven Property Analysis System")
    print("=" * 50)
    
    # Get a sample property analysis
    try:
        analysis = PropertyAnalysis.objects.filter(
            status='completed',
            asking_price__gt=0,
            total_area__gt=0
        ).first()
        
        if not analysis:
            print("❌ No completed property analysis found in database")
            print("Please run some property analyses first")
            return
        
        print(f"📊 Testing analysis for: {analysis.property_title}")
        print(f"📍 Location: {analysis.property_location}")
        print(f"💰 Price: €{analysis.asking_price:,.0f}")
        print(f"🏠 Area: {analysis.total_area}m²")
        print(f"📈 Current Score: {analysis.investment_score or 'N/A'}")
        print()
        
        # Run data-driven analysis
        analyzer = DataDrivenAnalyzer()
        result = analyzer.analyze_property(analysis)
        
        if result.get('status') == 'success':
            print("✅ Data-driven analysis completed successfully!")
            print()
            
            # Display key results
            print("📈 ANALYSIS RESULTS:")
            print("-" * 30)
            
            # Investment Score
            new_score = result.get('investment_score', 'N/A')
            print(f"Investment Score: {new_score}/100 (Data-Driven)")
            
            # Recommendation
            recommendation = result.get('recommendation', 'N/A')
            print(f"Recommendation: {recommendation.replace('_', ' ').title()}")
            
            # Market Position
            market_position = result.get('market_position_analysis', {})
            if market_position:
                percentile = market_position.get('market_percentile', 'N/A')
                sample_size = market_position.get('sample_size', 0)
                savings = market_position.get('potential_savings', 0)
                print(f"Market Position: {percentile}th percentile among {sample_size} comparable properties")
                if savings > 0:
                    print(f"Potential Savings: €{savings:,.0f}")
            
            # Investment Potential
            investment_potential = result.get('investment_potential', {})
            if investment_potential:
                gross_yield = investment_potential.get('gross_annual_yield', 0)
                net_yield = investment_potential.get('net_annual_yield', 0)
                total_return = investment_potential.get('projected_5y_total_return', 0)
                print(f"Gross Yield: {gross_yield:.1f}%")
                print(f"Net Yield: {net_yield:.1f}%")
                print(f"5-Year Return: {total_return:.1f}%")
            
            # Market Momentum
            market_momentum = result.get('market_momentum', {})
            if market_momentum:
                temperature = market_momentum.get('market_temperature', 'N/A')
                momentum = market_momentum.get('price_momentum_30d', 0)
                timing = market_momentum.get('timing_recommendation', 'N/A')
                print(f"Market Temperature: {temperature}")
                print(f"Price Momentum: {momentum:.1f}%")
                print(f"Timing: {timing.replace('_', ' ').title()}")
            
            # Agent Intelligence
            agent_intelligence = result.get('agent_intelligence', {})
            if agent_intelligence:
                portfolio_size = agent_intelligence.get('agent_portfolio_size', 0)
                vs_market = agent_intelligence.get('agent_avg_price_vs_market', 0)
                negotiation = agent_intelligence.get('negotiation_potential', 'N/A')
                print(f"Agent Properties: {portfolio_size}")
                print(f"Agent vs Market: {vs_market:+.1f}%")
                print(f"Negotiation Potential: {negotiation}")
            
            # Scarcity Analysis
            scarcity_analysis = result.get('scarcity_analysis', {})
            if scarcity_analysis:
                scarcity_score = scarcity_analysis.get('scarcity_score', 0)
                similar_active = scarcity_analysis.get('similar_active_count', 0)
                historical_demand = scarcity_analysis.get('historical_demand', 0)
                print(f"Scarcity Score: {scarcity_score}/100")
                print(f"Similar Available: {similar_active}")
                print(f"Historical Demand: {historical_demand} sold in 6 months")
            
            # Data Sources
            data_sources = result.get('data_sources', {})
            print(f"\n📊 Data Sources:")
            print(f"Comparable Properties: {data_sources.get('comparable_properties', 0)}")
            print(f"Agent Properties: {data_sources.get('agent_properties', 0)}")
            print(f"Market Data Points: {data_sources.get('market_data_points', 0)}")
            print(f"Analysis Method: {data_sources.get('analysis_method', 'N/A')}")
            
            # Market Insights
            market_insights = result.get('market_insights', [])
            if market_insights:
                print(f"\n💡 Key Insights:")
                for i, insight in enumerate(market_insights[:3], 1):
                    print(f"{i}. {insight}")
            
            # Action Items
            action_items = result.get('action_items', [])
            if action_items:
                print(f"\n🎯 Recommended Actions:")
                for i, action in enumerate(action_items[:3], 1):
                    print(f"{i}. {action}")
            
            print("\n✅ Data-driven analysis test completed successfully!")
            
        else:
            print(f"❌ Analysis failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_driven_analysis()
