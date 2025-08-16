# admin.py - Simplified admin interface
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import PropertyAnalysis
from .tasks import analyze_property_task, generate_property_report_task
import logging

logger = logging.getLogger(__name__)

def run_ai_analysis(modeladmin, request, queryset):
    """Run AI analysis on selected properties"""
    queued_count = 0
    skipped_count = 0
    
    for analysis in queryset:
        if analysis.status == 'completed':
            skipped_count += 1
            continue
            
        try:
            analyze_property_task.delay(analysis.id)
            analysis.status = 'analyzing'
            analysis.save()
            queued_count += 1
        except Exception as e:
            logger.error(f"Failed to queue analysis for property {analysis.id}: {str(e)}")
    
    if queued_count > 0:
        messages.success(request, f'Queued {queued_count} properties for AI analysis.')
    if skipped_count > 0:
        messages.info(request, f'Skipped {skipped_count} already completed analyses.')

run_ai_analysis.short_description = "🤖 Run AI Analysis"

def reset_analysis(modeladmin, request, queryset):
    """Reset analysis status to allow re-analysis"""
    reset_count = queryset.update(
        status='analyzing',
        analysis_result={},
        ai_summary='',
        investment_score=None,
        recommendation=None
    )
    messages.success(request, f'Reset {reset_count} property analyses.')

reset_analysis.short_description = "🔄 Reset Analysis"

def generate_reports(modeladmin, request, queryset):
    """Generate PDF reports for completed analyses"""
    queued_count = 0
    skipped_count = 0
    
    completed_analyses = queryset.filter(status='completed')
    
    for analysis in completed_analyses:
        if analysis.report_generated:
            skipped_count += 1
            continue
            
        try:
            generate_property_report_task.delay(analysis.id)
            queued_count += 1
        except Exception as e:
            logger.error(f"Failed to queue report for property {analysis.id}: {str(e)}")
    
    if queued_count > 0:
        messages.success(request, f'Queued {queued_count} reports for generation.')
    if skipped_count > 0:
        messages.info(request, f'Skipped {skipped_count} properties that already have reports.')

generate_reports.short_description = "📄 Generate PDF Reports"

def toggle_active_status(modeladmin, request, queryset):
    """Toggle active status of properties"""
    from django.utils import timezone
    
    active_count = queryset.filter(is_active=True).count()
    inactive_count = queryset.filter(is_active=False).count()
    
    if active_count > 0:
        queryset.filter(is_active=True).update(
            is_active=False,
            removed_date=timezone.now()
        )
        messages.success(request, f'Marked {active_count} properties as inactive.')
    
    if inactive_count > 0:
        queryset.filter(is_active=False).update(
            is_active=True,
            removed_date=None
        )
        messages.success(request, f'Marked {inactive_count} properties as active.')

toggle_active_status.short_description = "🔄 Toggle Active Status"

@admin.register(PropertyAnalysis)
class PropertyAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'property_title_short', 'property_location', 'asking_price_formatted',
        'investment_score_display', 'recommendation_badge', 'status_badge', 
        'is_active_display', 'created_at'
    ]
    list_filter = [
        'status', 'recommendation', 'property_type', 'property_location',
        'is_active', 'created_at', 'investment_score'
    ]
    search_fields = [
        'property_title', 'property_location', 'neighborhood', 'property_url', 
        'agent_name'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'price_per_sqm', 'usable_area',
        'days_on_market', 'analysis_result_display'
    ]
    ordering = ['-created_at']
    list_per_page = 25
    
    # Simplified actions
    actions = [
        run_ai_analysis,
        reset_analysis,
        generate_reports,
        toggle_active_status
    ]
    
    fieldsets = (
        ('Property Details', {
            'fields': (
                'property_url', 'property_title', 'property_location', 'neighborhood',
                'asking_price', 'property_type', 'property_condition'
            )
        }),
        ('Physical Attributes', {
            'fields': (
                'total_area', 'internal_area', 'bedrooms', 'bathrooms', 
                'floor_level', 'furnished', 'has_elevator'
            ),
            'classes': ('collapse',)
        }),
        ('Analysis Results', {
            'fields': (
                'investment_score', 'recommendation', 'ai_summary', 'status', 
                'analysis_result_display'
            )
        }),
        ('Market Status', {
            'fields': (
                'is_active', 'removed_date', 'days_on_market'
            ),
            'classes': ('collapse',)
        }),
        ('Agent Information', {
            'fields': ('agent_name', 'agent_email', 'agent_phone'),
            'classes': ('collapse',)
        }),
        ('User & Processing', {
            'fields': (
                'user', 'scraped_by', 'report_generated', 'report_file_path', 
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def property_title_short(self, obj):
        title = obj.property_title[:60] + "..." if len(obj.property_title) > 60 else obj.property_title
        if obj.status == 'completed':
            try:
                url = reverse('property_ai:analysis_detail', args=[obj.id])
                return format_html(
                    '<a href="{}" target="_blank">{}</a>', 
                    url, title
                )
            except:
                return title
        return title
    property_title_short.short_description = "Property Title"
    
    def asking_price_formatted(self, obj):
        return f"€{obj.asking_price:,.0f}"
    asking_price_formatted.short_description = "Price"
    asking_price_formatted.admin_order_field = 'asking_price'
    
    def investment_score_display(self, obj):
        if obj.investment_score is not None:
            if obj.investment_score >= 80:
                color = '#10b981'
                icon = '🟢'
            elif obj.investment_score >= 60:
                color = '#3b82f6'
                icon = '🔵'
            elif obj.investment_score >= 40:
                color = '#f59e0b'
                icon = '🟡'
            else:
                color = '#ef4444'
                icon = '🔴'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} {}</span>',
                color, icon, obj.investment_score
            )
        return format_html('<span style="color: #9ca3af;">-</span>')
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
                '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                color, obj.get_recommendation_display()
            )
        return format_html('<span style="color: #9ca3af;">-</span>')
    recommendation_badge.short_description = "Recommendation"
    recommendation_badge.admin_order_field = 'recommendation'
    
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
    status_badge.admin_order_field = 'status'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #10b981;">🟢 Active</span>')
        else:
            return format_html('<span style="color: #ef4444;">🔴 Inactive</span>')
    is_active_display.short_description = "Market Status"
    is_active_display.admin_order_field = 'is_active'
    
    def analysis_result_display(self, obj):
        """Display formatted analysis results"""
        if not obj.analysis_result:
            return "No analysis data"
            
        result = obj.analysis_result
        html = "<div style='max-width: 600px; font-size: 13px;'>"
        
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
            for insight in result['market_insights'][:3]:
                html += f"<li>{insight}</li>"
            html += "</ul>"
        
        html += "</div>"
        return mark_safe(html)
    analysis_result_display.short_description = "Analysis Details"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('user', 'scraped_by')

from django.contrib import admin
from .models import ComingSoonSubscription

@admin.register(ComingSoonSubscription)
class ComingSoonSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']
    list_filter = ['subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at']
    ordering = ['-subscribed_at']