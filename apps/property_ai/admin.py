# admin.py - Enhanced admin interface with AI analysis actions
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PropertyAnalysis
from .tasks import analyze_property_task
from .ai_engine import PropertyAI
import logging

logger = logging.getLogger(__name__)

def run_ai_analysis_sync(modeladmin, request, queryset):
    """Run AI analysis synchronously (for small batches)"""
    success_count = 0
    error_count = 0
    
    for analysis in queryset:
        if analysis.status == 'completed':
            messages.warning(request, f'Property "{analysis.property_title[:50]}" already has completed analysis.')
            continue
            
        try:
            # Update status
            analysis.status = 'analyzing'
            analysis.processing_stage = 'ai_analysis'
            analysis.save()
            
            # Prepare data for AI analysis
            analysis_data = {
                'title': analysis.property_title,
                'location': analysis.property_location,
                'neighborhood': analysis.neighborhood,
                'price': float(analysis.asking_price),
                'property_type': analysis.property_type,
                'square_meters': analysis.total_area,
                'condition': analysis.property_condition,
                'floor_level': analysis.floor_level,
            }
            
            # Get comparable properties
            from .views import get_comparable_properties
            comparable_properties = get_comparable_properties(analysis)
            
            # Run AI analysis
            ai = PropertyAI()
            result = ai.analyze_property(analysis_data, comparable_properties)
            
            if result.get('status') == 'success':
                # Save results
                analysis.analysis_result = result
                analysis.ai_summary = result.get('summary', '')
                analysis.investment_score = result.get('investment_score')
                analysis.recommendation = result.get('recommendation')
                analysis.status = 'completed'
                analysis.processing_stage = 'completed'
                analysis.save()
                success_count += 1
                
                logger.info(f"Successfully analyzed property {analysis.id}")
            else:
                analysis.status = 'failed'
                analysis.processing_stage = 'failed'
                analysis.save()
                error_count += 1
                logger.error(f"AI analysis failed for property {analysis.id}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            analysis.status = 'failed'
            analysis.processing_stage = 'failed'
            analysis.save()
            error_count += 1
            logger.error(f"Error analyzing property {analysis.id}: {str(e)}")
    
    # Show results
    if success_count > 0:
        messages.success(request, f'Successfully analyzed {success_count} properties.')
    if error_count > 0:
        messages.error(request, f'Failed to analyze {error_count} properties. Check logs for details.')

run_ai_analysis_sync.short_description = "🤖 Run AI Analysis (Sync)"

def run_ai_analysis_async(modeladmin, request, queryset):
    """Run AI analysis asynchronously using Celery tasks"""
    queued_count = 0
    skipped_count = 0
    
    for analysis in queryset:
        if analysis.status == 'completed':
            skipped_count += 1
            continue
            
        # Queue for async processing
        analyze_property_task.delay(analysis.id)
        analysis.status = 'analyzing'
        analysis.processing_stage = 'queued'
        analysis.save()
        queued_count += 1
    
    if queued_count > 0:
        messages.success(request, f'Queued {queued_count} properties for AI analysis.')
    if skipped_count > 0:
        messages.info(request, f'Skipped {skipped_count} already completed analyses.')

run_ai_analysis_async.short_description = "⚡ Queue AI Analysis (Async)"

def reset_analysis_status(modeladmin, request, queryset):
    """Reset analysis status to allow re-analysis"""
    reset_count = queryset.update(
        status='analyzing',
        processing_stage='reset',
        analysis_result={},
        ai_summary='',
        investment_score=None,
        recommendation=None
    )
    messages.success(request, f'Reset {reset_count} property analyses. You can now re-run AI analysis.')

reset_analysis_status.short_description = "🔄 Reset Analysis Status"

def generate_reports(modeladmin, request, queryset):
    """Generate PDF reports for completed analyses"""
    from .tasks import generate_property_report_task
    
    queued_count = 0
    skipped_count = 0
    
    for analysis in queryset.filter(status='completed'):
        if analysis.report_generated:
            skipped_count += 1
            continue
            
        generate_property_report_task.delay(analysis.id)
        queued_count += 1
    
    if queued_count > 0:
        messages.success(request, f'Queued {queued_count} reports for generation.')
    if skipped_count > 0:
        messages.info(request, f'Skipped {skipped_count} properties that already have reports.')

generate_reports.short_description = "📄 Generate PDF Reports"

def mark_as_removed(modeladmin, request, queryset):
    """Mark properties as removed/inactive"""
    from django.utils import timezone
    
    updated_count = queryset.update(
        is_active=False,
        removed_date=timezone.now()
    )
    messages.success(request, f'Marked {updated_count} properties as removed.')

mark_as_removed.short_description = "❌ Mark as Removed"

def mark_as_active(modeladmin, request, queryset):
    """Mark properties as active again"""
    updated_count = queryset.update(
        is_active=True,
        removed_date=None
    )
    messages.success(request, f'Marked {updated_count} properties as active.')

mark_as_active.short_description = "✅ Mark as Active"

@admin.register(PropertyAnalysis)
class PropertyAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'property_title_short', 'property_location', 'asking_price_formatted',
        'investment_score_display', 'recommendation_badge', 'status_badge', 
        'is_active_display', 'days_on_market_display', 'created_at'
    ]
    list_filter = [
        'status', 'recommendation', 'property_type', 'property_location',
        'is_active', 'created_at', 'investment_score', 'property_condition'
    ]
    search_fields = [
        'property_title', 'property_location', 'neighborhood', 'property_url', 'property_id'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'price_per_sqm', 'usable_area',
        'days_on_market', 'analysis_result_display'
    ]
    ordering = ['-created_at']
    
    # Add the custom actions
    actions = [
        run_ai_analysis_sync,
        run_ai_analysis_async, 
        reset_analysis_status,
        generate_reports,
        mark_as_removed,
        mark_as_active
    ]
    
    fieldsets = (
        ('Property Details', {
            'fields': ('property_url', 'property_title', 'property_location', 'neighborhood',
                      'asking_price', 'property_type', 'property_condition')
        }),
        ('Physical Attributes', {
            'fields': ('total_area', 'internal_area', 'bedrooms', 'bathrooms', 'floor_level'),
            'classes': ('collapse',)
        }),
        ('Analysis Results', {
            'fields': ('investment_score', 'recommendation', 'ai_summary', 'status', 'analysis_result_display')
        }),
        ('Market Status', {
            'fields': ('is_active', 'last_checked', 'removed_date', 'days_on_market'),
            'classes': ('collapse',)
        }),
        ('User & Processing', {
            'fields': ('user', 'report_generated', 'report_file_path', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def property_title_short(self, obj):
        title = obj.property_title[:60] + "..." if len(obj.property_title) > 60 else obj.property_title
        # Add link to view analysis
        if obj.status == 'completed':
            url = reverse('property_ai:analysis_detail', args=[obj.id])
            return format_html('<a href="{}" target="_blank" title="View Analysis">{}</a>', url, title)
        return title
    property_title_short.short_description = "Property Title"
    
    def asking_price_formatted(self, obj):
        return f"€{obj.asking_price:,.0f}"
    asking_price_formatted.short_description = "Price"
    asking_price_formatted.admin_order_field = 'asking_price'
    
    def investment_score_display(self, obj):
        if obj.investment_score:
            if obj.investment_score >= 80:
                color = '#10b981'  # Green
            elif obj.investment_score >= 60:
                color = '#3b82f6'  # Blue
            elif obj.investment_score >= 40:
                color = '#f59e0b'  # Orange
            else:
                color = '#ef4444'  # Red
            
            return format_html(
                '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span>',
                color, obj.investment_score
            )
        return "-"
    investment_score_display.short_description = "Score"
    investment_score_display.admin_order_field = 'investment_score'
    
    def recommendation_badge(self, obj):
        colors = {
            'strong_buy': '#10b981',
            'buy': '#3b82f6', 
            'hold': '#f59e0b',
            'avoid': '#ef4444'
        }
        if obj.recommendation:
            color = colors.get(obj.recommendation, '#6b7280')
            return format_html(
                '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{}</span>',
                color, obj.get_recommendation_display()
            )
        return "-"
    recommendation_badge.short_description = "Recommendation"
    
    def status_badge(self, obj):
        colors = {
            'completed': '#10b981', 
            'analyzing': '#f59e0b', 
            'failed': '#ef4444'
        }
        icons = {
            'completed': '✅',
            'analyzing': '⏳', 
            'failed': '❌'
        }
        
        color = colors.get(obj.status, '#6b7280')
        icon = icons.get(obj.status, '⚪')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #10b981;">🟢 Active</span>')
        else:
            return format_html('<span style="color: #ef4444;">🔴 Removed</span>')
    is_active_display.short_description = "Market Status"
    is_active_display.admin_order_field = 'is_active'
    
    def days_on_market_display(self, obj):
        days = obj.days_on_market
        if days <= 7:
            color = '#10b981'  # Green for fresh listings
        elif days <= 30:
            color = '#3b82f6'  # Blue for recent
        elif days <= 90:
            color = '#f59e0b'  # Orange for aging
        else:
            color = '#ef4444'  # Red for stale
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>',
            color, days
        )
    days_on_market_display.short_description = "Days on Market"
    
    def analysis_result_display(self, obj):
        """Display formatted analysis results"""
        if not obj.analysis_result:
            return "No analysis data"
            
        result = obj.analysis_result
        html = "<div style='max-width: 500px;'>"
        
        # Price analysis
        if 'price_analysis' in result:
            price_data = result['price_analysis']
            html += "<h4>Price Analysis:</h4><ul>"
            if 'market_position_percentage' in price_data:
                pos = price_data['market_position_percentage']
                color = '#10b981' if pos < 0 else '#ef4444'
                html += f"<li style='color: {color};'>Market Position: {pos:+.1f}%</li>"
            if 'negotiation_potential' in price_data:
                html += f"<li>Negotiation: {price_data['negotiation_potential']}</li>"
            html += "</ul>"
        
        # Rental analysis
        if 'rental_analysis' in result:
            rental_data = result['rental_analysis']
            html += "<h4>Rental Analysis:</h4><ul>"
            if 'estimated_monthly_rent' in rental_data:
                html += f"<li>Est. Rent: €{rental_data['estimated_monthly_rent']}/month</li>"
            if 'annual_gross_yield' in rental_data:
                html += f"<li>Yield: {rental_data['annual_gross_yield']}</li>"
            html += "</ul>"
        
        # Market insights
        if 'market_insights' in result and result['market_insights']:
            html += f"<h4>Key Insights:</h4><ul>"
            for insight in result['market_insights'][:3]:  # Show top 3
                html += f"<li>{insight}</li>"
            html += "</ul>"
        
        html += "</div>"
        return mark_safe(html)
    analysis_result_display.short_description = "Analysis Details"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('user')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        # If manually changing status to analyzing, clear previous results
        if obj.status == 'analyzing' and change:
            obj.analysis_result = {}
            obj.ai_summary = ''
            obj.investment_score = None
            obj.recommendation = None
            
        super().save_model(request, obj, form, change)