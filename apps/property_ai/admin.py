# admin.py - Enhanced admin interface with AI analysis actions
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import PropertyAnalysis, ScrapingProgress
from .tasks import analyze_property_task
from .ai_engine import PropertyAI
import logging
import json

logger = logging.getLogger(__name__)

def run_ai_analysis_sync(modeladmin, request, queryset):
    """Run AI analysis synchronously (for small batches)"""
    if queryset.count() > 10:
        messages.warning(request, 'For performance reasons, sync analysis is limited to 10 properties. Use async for larger batches.')
        return
    
    success_count = 0
    error_count = 0
    
    for analysis in queryset:
        if analysis.status == 'completed':
            messages.warning(request, f'Property "{analysis.property_title[:50]}" already has completed analysis.')
            continue
            
        try:
            with transaction.atomic():
                # Update status
                analysis.status = 'analyzing'
                analysis.processing_stage = 'ai_analysis'
                analysis.save()
                
                # Prepare data for AI analysis
                analysis_data = {
                    'title': analysis.property_title,
                    'location': analysis.property_location,
                    'neighborhood': analysis.neighborhood or '',
                    'price': float(analysis.asking_price),
                    'property_type': analysis.property_type,
                    'square_meters': analysis.total_area,
                    'internal_area': analysis.internal_area,
                    'bedrooms': analysis.bedrooms,
                    'bathrooms': float(analysis.bathrooms) if analysis.bathrooms else None,
                    'condition': analysis.property_condition,
                    'floor_level': analysis.floor_level,
                    'furnished': analysis.furnished,
                    'has_elevator': analysis.has_elevator,
                    'description': analysis.description,
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
                    analysis.processing_stage = f'failed: {result.get("message", "Unknown error")[:100]}'
                    analysis.save()
                    error_count += 1
                    logger.error(f"AI analysis failed for property {analysis.id}: {result.get('message', 'Unknown error')}")
                    
        except Exception as e:
            analysis.status = 'failed'
            analysis.processing_stage = f'error: {str(e)[:100]}'
            analysis.save()
            error_count += 1
            logger.error(f"Error analyzing property {analysis.id}: {str(e)}", exc_info=True)
    
    # Show results
    if success_count > 0:
        messages.success(request, f'Successfully analyzed {success_count} properties.')
    if error_count > 0:
        messages.error(request, f'Failed to analyze {error_count} properties. Check logs for details.')

run_ai_analysis_sync.short_description = "🤖 Run AI Analysis (Sync - Max 10)"

def run_ai_analysis_async(modeladmin, request, queryset):
    """Run AI analysis asynchronously using Celery tasks"""
    queued_count = 0
    skipped_count = 0
    
    for analysis in queryset:
        if analysis.status == 'completed':
            skipped_count += 1
            continue
            
        try:
            # Queue for async processing
            analyze_property_task.delay(analysis.id)
            analysis.status = 'analyzing'
            analysis.processing_stage = 'queued'
            analysis.save()
            queued_count += 1
        except Exception as e:
            logger.error(f"Failed to queue analysis for property {analysis.id}: {str(e)}")
            messages.error(request, f'Failed to queue property {analysis.id}: {str(e)}')
    
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
    
    not_completed = queryset.exclude(status='completed').count()
    if not_completed > 0:
        messages.warning(request, f'{not_completed} properties are not completed and were skipped.')

generate_reports.short_description = "📄 Generate PDF Reports"

def mark_as_removed(modeladmin, request, queryset):
    """Mark properties as removed/inactive"""
    from django.utils import timezone
    
    updated_count = queryset.filter(is_active=True).update(
        is_active=False,
        removed_date=timezone.now()
    )
    messages.success(request, f'Marked {updated_count} properties as removed.')

mark_as_removed.short_description = "❌ Mark as Removed"

def mark_as_active(modeladmin, request, queryset):
    """Mark properties as active again"""
    updated_count = queryset.filter(is_active=False).update(
        is_active=True,
        removed_date=None
    )
    messages.success(request, f'Marked {updated_count} properties as active.')

mark_as_active.short_description = "✅ Mark as Active"

def export_analysis_data(modeladmin, request, queryset):
    """Export selected analyses as JSON"""
    import json
    from django.http import JsonResponse
    
    data = []
    for analysis in queryset:
        data.append({
            'id': str(analysis.id),
            'title': analysis.property_title,
            'location': analysis.property_location,
            'price': str(analysis.asking_price),
            'investment_score': analysis.investment_score,
            'recommendation': analysis.recommendation,
            'status': analysis.status,
            'created_at': analysis.created_at.isoformat(),
            'analysis_result': analysis.analysis_result,
        })
    
    response = HttpResponse(
        json.dumps(data, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="property_analyses.json"'
    return response

export_analysis_data.short_description = "📊 Export Analysis Data (JSON)"

@admin.register(PropertyAnalysis)
class PropertyAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'property_title_short', 'property_location', 'asking_price_formatted',
        'investment_score_display', 'recommendation_badge', 'status_badge', 
        'is_active_display', 'days_on_market_display', 'user_display', 'created_at'
    ]
    list_filter = [
        'status', 'recommendation', 'property_type', 'property_location',
        'is_active', 'created_at', 'investment_score', 'property_condition',
        'scraped_by', 'user'
    ]
    search_fields = [
        'property_title', 'property_location', 'neighborhood', 'property_url', 
        'property_id', 'listing_code', 'agent_name'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'price_per_sqm', 'usable_area',
        'days_on_market', 'analysis_result_display', 'processing_stage'
    ]
    ordering = ['-created_at']
    list_per_page = 25
    
    # Add the custom actions
    actions = [
        run_ai_analysis_sync,
        run_ai_analysis_async, 
        reset_analysis_status,
        generate_reports,
        mark_as_removed,
        mark_as_active,
        export_analysis_data
    ]
    
    fieldsets = (
        ('Property Details', {
            'fields': (
                'property_url', 'property_title', 'property_location', 'neighborhood',
                'asking_price', 'property_type', 'property_condition', 'property_id', 'listing_code'
            )
        }),
        ('Physical Attributes', {
            'fields': (
                'total_area', 'internal_area', 'usable_area', 'bedrooms', 'bathrooms', 
                'floor_level', 'ceiling_height', 'facade_length', 'furnished', 'has_elevator'
            ),
            'classes': ('collapse',)
        }),
        ('Analysis Results', {
            'fields': (
                'investment_score', 'recommendation', 'ai_summary', 'status', 
                'processing_stage', 'analysis_result_display'
            )
        }),
        ('Market Status', {
            'fields': (
                'is_active', 'last_checked', 'removed_date', 'days_on_market', 'view_count'
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
        # Add link to view analysis if completed
        if obj.status == 'completed':
            try:
                url = reverse('property_ai:analysis_detail', args=[obj.id])
                return format_html(
                    '<a href="{}" target="_blank" title="View Analysis" style="text-decoration: none;">{}</a>', 
                    url, title
                )
            except:
                # Fallback if URL pattern doesn't exist
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
                color = '#10b981'  # Green
                icon = '🟢'
            elif obj.investment_score >= 60:
                color = '#3b82f6'  # Blue
                icon = '🔵'
            elif obj.investment_score >= 40:
                color = '#f59e0b'  # Orange
                icon = '🟡'
            else:
                color = '#ef4444'  # Red
                icon = '🔴'
            
            return format_html(
                '<span style="color: {}; font-weight: bold; font-size: 16px;">{} {}</span>',
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
                '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{}</span>',
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
        
        status_text = obj.get_status_display()
        if obj.processing_stage and obj.processing_stage != obj.status:
            status_text += f" ({obj.processing_stage})"
        
        return format_html(
            '<span style="color: {}; font-weight: bold;" title="{}">{} {}</span>',
            color, obj.processing_stage or '', icon, status_text
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #10b981;">🟢 Active</span>')
        else:
            removed_text = ""
            if obj.removed_date:
                removed_text = f" ({obj.removed_date.strftime('%Y-%m-%d')})"
            return format_html('<span style="color: #ef4444;" title="Removed{}">🔴 Removed</span>', removed_text)
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
    
    def user_display(self, obj):
        """Display user and scraped_by information"""
        if obj.user:
            user_text = obj.user.username
            if obj.scraped_by and obj.scraped_by != obj.user:
                user_text += f" (scraped by {obj.scraped_by.username})"
            return user_text
        elif obj.scraped_by:
            return f"Scraped by {obj.scraped_by.username}"
        return "-"
    user_display.short_description = "User"
    
    def analysis_result_display(self, obj):
        """Display formatted analysis results"""
        if not obj.analysis_result:
            return "No analysis data"
            
        result = obj.analysis_result
        html = "<div style='max-width: 600px; font-size: 13px;'>"
        
        # Price analysis
        if 'price_analysis' in result:
            price_data = result['price_analysis']
            html += "<h4 style='margin: 10px 0 5px 0; color: #374151;'>Price Analysis:</h4><ul style='margin: 5px 0; padding-left: 20px;'>"
            if 'market_position_percentage' in price_data:
                pos = price_data['market_position_percentage']
                color = '#10b981' if pos < 0 else '#ef4444'
                html += f"<li style='color: {color}; margin-bottom: 3px;'>Market Position: {pos:+.1f}%</li>"
            if 'negotiation_potential' in price_data:
                html += f"<li style='margin-bottom: 3px;'>Negotiation: {price_data['negotiation_potential']}</li>"
            if 'price_per_sqm' in price_data:
                html += f"<li style='margin-bottom: 3px;'>Price/m²: €{price_data['price_per_sqm']:.0f}</li>"
            html += "</ul>"
        
        # Rental analysis
        if 'rental_analysis' in result:
            rental_data = result['rental_analysis']
            html += "<h4 style='margin: 10px 0 5px 0; color: #374151;'>Rental Analysis:</h4><ul style='margin: 5px 0; padding-left: 20px;'>"
            if 'estimated_monthly_rent' in rental_data:
                html += f"<li style='margin-bottom: 3px;'>Est. Rent: €{rental_data['estimated_monthly_rent']}/month</li>"
            if 'annual_gross_yield' in rental_data:
                html += f"<li style='margin-bottom: 3px;'>Yield: {rental_data['annual_gross_yield']}</li>"
            if 'roi_timeline' in rental_data:
                html += f"<li style='margin-bottom: 3px;'>ROI Timeline: {rental_data['roi_timeline']}</li>"
            html += "</ul>"
        
        # Market insights
        if 'market_insights' in result and result['market_insights']:
            html += f"<h4 style='margin: 10px 0 5px 0; color: #374151;'>Key Insights:</h4><ul style='margin: 5px 0; padding-left: 20px;'>"
            for insight in result['market_insights'][:3]:  # Show top 3
                html += f"<li style='margin-bottom: 3px;'>{insight}</li>"
            html += "</ul>"
        
        # Risk factors
        if 'risk_factors' in result and result['risk_factors']:
            html += f"<h4 style='margin: 10px 0 5px 0; color: #dc2626;'>Risk Factors:</h4><ul style='margin: 5px 0; padding-left: 20px;'>"
            for risk in result['risk_factors'][:2]:  # Show top 2
                html += f"<li style='margin-bottom: 3px; color: #dc2626;'>{risk}</li>"
            html += "</ul>"
        
        html += "</div>"
        return mark_safe(html)
    analysis_result_display.short_description = "Analysis Details"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('user', 'scraped_by')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        # If manually changing status to analyzing, clear previous results
        if obj.status == 'analyzing' and change:
            if 'status' in form.changed_data:
                obj.analysis_result = {}
                obj.ai_summary = ''
                obj.investment_score = None
                obj.recommendation = None
                obj.processing_stage = 'manual_reset'
            
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """Custom permission logic"""
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        """Restrict deletion to superusers"""
        return request.user.is_superuser


@admin.register(ScrapingProgress)
class ScrapingProgressAdmin(admin.ModelAdmin):
    list_display = ['id', 'last_scraped_page', 'total_properties_found', 'bootstrap_complete', 'last_update']
    readonly_fields = ['last_update']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not ScrapingProgress.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
from django.contrib import admin
from .models import ComingSoonSubscription

@admin.register(ComingSoonSubscription)
class ComingSoonSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']
    list_filter = ['subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at']
    ordering = ['-subscribed_at']