from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.analytics import PropertyAnalytics
from apps.property_ai.market_engines import MarketPositionEngine, AgentPerformanceAnalyzer
from apps.property_ai.utils import performance_monitor, log_system_health
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test performance improvements and system health'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-cache',
            action='store_true',
            help='Test caching performance',
        )
        parser.add_argument(
            '--test-queries',
            action='store_true',
            help='Test database query optimization',
        )
        parser.add_argument(
            '--test-analytics',
            action='store_true',
            help='Test analytics performance',
        )
        parser.add_argument(
            '--full-test',
            action='store_true',
            help='Run all performance tests',
        )

    @performance_monitor("test_analytics_performance")
    def test_analytics_performance(self):
        """Test analytics performance with caching"""
        analytics = PropertyAnalytics()
        
        # Get a sample property for testing
        sample_property = PropertyAnalysis.objects.filter(
            status='completed',
            property_location__isnull=False
        ).first()
        
        if not sample_property:
            self.stdout.write(self.style.WARNING("No completed properties found for testing"))
            return
        
        location = sample_property.property_location.split(',')[0]
        
        # Test market stats (should use cache on second call)
        start_time = time.time()
        market_stats = analytics.get_location_market_stats(location)
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        market_stats_cached = analytics.get_location_market_stats(location)
        second_call_time = time.time() - start_time
        
        # Test price trends
        start_time = time.time()
        price_trends = analytics.get_price_trends(location)
        trends_first_call = time.time() - start_time
        
        start_time = time.time()
        price_trends_cached = analytics.get_price_trends(location)
        trends_second_call = time.time() - start_time
        
        # Test comparable analysis
        start_time = time.time()
        comparable = analytics.get_comparable_analysis(sample_property)
        comparable_first_call = time.time() - start_time
        
        start_time = time.time()
        comparable_cached = analytics.get_comparable_analysis(sample_property)
        comparable_second_call = time.time() - start_time
        
        self.stdout.write(self.style.SUCCESS(f"Analytics Performance Test Results:"))
        self.stdout.write(f"  Market Stats: {first_call_time:.3f}s → {second_call_time:.3f}s ({(1-second_call_time/first_call_time)*100:.1f}% improvement)")
        self.stdout.write(f"  Price Trends: {trends_first_call:.3f}s → {trends_second_call:.3f}s ({(1-trends_second_call/trends_first_call)*100:.1f}% improvement)")
        self.stdout.write(f"  Comparable Analysis: {comparable_first_call:.3f}s → {comparable_second_call:.3f}s ({(1-comparable_second_call/comparable_first_call)*100:.1f}% improvement)")

    @performance_monitor("test_market_engines")
    def test_market_engines(self):
        """Test market engines performance"""
        # Get a sample property
        sample_property = PropertyAnalysis.objects.filter(
            status='completed',
            property_location__isnull=False,
            agent_name__isnull=False
        ).first()
        
        if not sample_property:
            self.stdout.write(self.style.WARNING("No suitable properties found for market engine testing"))
            return
        
        # Test market position engine
        market_engine = MarketPositionEngine()
        start_time = time.time()
        market_position = market_engine.calculate_property_advantage(sample_property)
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        market_position_cached = market_engine.calculate_property_advantage(sample_property)
        second_call_time = time.time() - start_time
        
        # Test agent analyzer
        agent_analyzer = AgentPerformanceAnalyzer()
        start_time = time.time()
        agent_insights = agent_analyzer.get_agent_insights(sample_property)
        agent_first_call = time.time() - start_time
        
        start_time = time.time()
        agent_insights_cached = agent_analyzer.get_agent_insights(sample_property)
        agent_second_call = time.time() - start_time
        
        self.stdout.write(self.style.SUCCESS(f"Market Engines Performance Test Results:"))
        if market_position:
            self.stdout.write(f"  Market Position: {first_call_time:.3f}s → {second_call_time:.3f}s ({(1-second_call_time/first_call_time)*100:.1f}% improvement)")
        if agent_insights:
            self.stdout.write(f"  Agent Insights: {agent_first_call:.3f}s → {agent_second_call:.3f}s ({(1-agent_second_call/agent_first_call)*100:.1f}% improvement)")

    @performance_monitor("test_database_queries")
    def test_database_queries(self):
        """Test database query optimization"""
        from django.db import connection
        
        # Reset query count
        connection.queries = []
        
        # Test optimized query
        start_time = time.time()
        analyses = PropertyAnalysis.objects.filter(
            status='completed'
        ).select_related('user').order_by('-created_at')[:10]
        
        # Force evaluation
        list(analyses)
        optimized_time = time.time() - start_time
        optimized_queries = len(connection.queries)
        
        # Reset for unoptimized test
        connection.queries = []
        
        # Test unoptimized query (simulate N+1)
        start_time = time.time()
        analyses_unoptimized = PropertyAnalysis.objects.filter(
            status='completed'
        ).order_by('-created_at')[:10]
        
        # Force evaluation and access user (causing N+1)
        for analysis in analyses_unoptimized:
            _ = analysis.user.username if analysis.user else None
        
        unoptimized_time = time.time() - start_time
        unoptimized_queries = len(connection.queries)
        
        self.stdout.write(self.style.SUCCESS(f"Database Query Optimization Test Results:"))
        self.stdout.write(f"  Optimized: {optimized_queries} queries in {optimized_time:.3f}s")
        self.stdout.write(f"  Unoptimized: {unoptimized_queries} queries in {unoptimized_time:.3f}s")
        self.stdout.write(f"  Query reduction: {((unoptimized_queries-optimized_queries)/unoptimized_queries)*100:.1f}%")
        self.stdout.write(f"  Time improvement: {((unoptimized_time-optimized_time)/unoptimized_time)*100:.1f}%")

    def test_system_health(self):
        """Test overall system health"""
        self.stdout.write(self.style.SUCCESS("System Health Check:"))
        
        # Log system health
        log_system_health()
        
        # Basic stats
        total_properties = PropertyAnalysis.objects.count()
        completed_analyses = PropertyAnalysis.objects.filter(status='completed').count()
        failed_analyses = PropertyAnalysis.objects.filter(status='failed').count()
        
        self.stdout.write(f"  Total Properties: {total_properties}")
        self.stdout.write(f"  Completed Analyses: {completed_analyses}")
        self.stdout.write(f"  Failed Analyses: {failed_analyses}")
        
        if completed_analyses > 0:
            success_rate = ((completed_analyses - failed_analyses) / completed_analyses) * 100
            self.stdout.write(f"  Success Rate: {success_rate:.1f}%")
            
            if success_rate < 90:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Low success rate detected: {success_rate:.1f}%"))
            else:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Good success rate: {success_rate:.1f}%"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Performance Tests..."))
        
        if options['full_test'] or options['test_analytics']:
            self.stdout.write("\n" + "="*50)
            self.stdout.write("Testing Analytics Performance...")
            self.test_analytics_performance()
        
        if options['full_test'] or options['test_queries']:
            self.stdout.write("\n" + "="*50)
            self.stdout.write("Testing Database Query Optimization...")
            self.test_database_queries()
        
        if options['full_test']:
            self.stdout.write("\n" + "="*50)
            self.stdout.write("Testing Market Engines...")
            self.test_market_engines()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("System Health Check...")
        self.test_system_health()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("Performance Tests Completed!"))
        self.stdout.write("Check the logs for detailed performance metrics.")
