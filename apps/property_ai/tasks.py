import logging
import os
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from .models import PropertyAnalysis
from .ai_engine import PropertyAI
from .report_generator import PropertyReportPDF
import random
import time

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_property_report_task(self, property_analysis_id):
    """Generate comprehensive property report PDF"""
    try:
        property_analysis = PropertyAnalysis.objects.get(id=property_analysis_id)
        
        property_analysis.processing_stage = 'creating_pdf'
        property_analysis.save()

        # Generate report content
        ai = PropertyAI()
        report_content = ai.generate_report(property_analysis)

        # Generate PDF
        pdf_generator = PropertyReportPDF()
        pdf_file_path = pdf_generator.generate_pdf_report(
            property_analysis=property_analysis,
            report_content=report_content
        )

        property_analysis.processing_stage = 'completed'
        property_analysis.report_generated = True
        property_analysis.report_file_path = pdf_file_path
        property_analysis.save()
        
        logger.info(f"Successfully generated report for analysis {property_analysis_id}")

        # Send email with PDF if user exists
        if property_analysis.user and property_analysis.user.email:
            send_report_email.delay(property_analysis_id)

        return f"Report generated successfully: {pdf_file_path}"
    except PropertyAnalysis.DoesNotExist:
        logger.error(f"Property analysis {property_analysis_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error generating report for analysis {property_analysis_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            raise

@shared_task
def send_report_email(property_analysis_id):
    """Send the PDF report via email to the user"""
    try:
        analysis = PropertyAnalysis.objects.get(id=property_analysis_id)
        if analysis.report_generated and analysis.report_file_path and analysis.user:
            subject = "Your AI Property Analysis Report is Ready!"
            
            body = f"""
            Hi {analysis.user.username},
            
            Your property analysis report is ready!
            
            Property: {analysis.property_title}
            Location: {analysis.property_location}
            
            Please find your detailed analysis report attached.
            
            Best regards,
            AI Property Analysis Team
            """
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[analysis.user.email]
            )
            
            if os.path.exists(analysis.report_file_path):
                with open(analysis.report_file_path, 'rb') as f:
                    email.attach('PropertyReport.pdf', f.read(), 'application/pdf')
            
            email.send()
            logger.info(f"Sent report email to {analysis.user.email} for analysis {analysis.id}")
        else:
            logger.warning(f"Report email not sent for analysis {property_analysis_id}: report not ready or no user.")
    except PropertyAnalysis.DoesNotExist:
        logger.error(f"Property analysis {property_analysis_id} not found for email sending")
    except Exception as e:
        logger.error(f"Error sending report email for analysis {property_analysis_id}: {str(e)}")

    
@shared_task
def check_property_urls_task():
    """Celery task to check property URL status"""
    from django.core.management import call_command
    
    try:
        # Run the management command
        call_command('check_property_urls', '--days-old=7', '--limit=50')
        logger.info("Property URL check completed successfully")
        return "Property URL check completed"
    except Exception as e:
        logger.error(f"Property URL check failed: {e}")
        return f"Error: {e}"
    
# apps/property_ai/tasks.py (add this to your existing tasks.py)

@shared_task(bind=True, max_retries=3)
def analyze_property_task(self, property_analysis_id):
    """Run AI analysis on a scraped property"""
    try:
        property_analysis = PropertyAnalysis.objects.get(id=property_analysis_id)
        
        if property_analysis.status != 'analyzing':
            return f"Property {property_analysis_id} not in analyzing status"
        
        property_analysis.processing_stage = 'ai_analysis'
        property_analysis.save()
        
        # Prepare data for AI analysis
        analysis_data = {
            'title': property_analysis.property_title,
            'location': property_analysis.property_location,
            'neighborhood': property_analysis.neighborhood,  # NOW INCLUDED
            'price': float(property_analysis.asking_price),
            'property_type': property_analysis.property_type,
            'square_meters': property_analysis.total_area,
            'condition': property_analysis.property_condition,
            'floor_level': property_analysis.floor_level,
        }
        
        # Get comparable properties
        from apps.property_ai.views import get_comparable_properties
        comparable_properties = get_comparable_properties(property_analysis)
        
        # Run AI analysis
        ai = PropertyAI()
        result = ai.analyze_property(analysis_data, comparable_properties)
        
        if result.get('status') == 'success':
            # Save results
            property_analysis.analysis_result = result
            property_analysis.ai_summary = result.get('summary', '')
            property_analysis.investment_score = result.get('investment_score')
            property_analysis.recommendation = result.get('recommendation')
            property_analysis.status = 'completed'
            property_analysis.processing_stage = 'completed'
            property_analysis.save()
            
            logger.info(f"Successfully analyzed property {property_analysis_id}")
            return f"Analysis completed for property {property_analysis_id}"
        else:
            property_analysis.status = 'failed'
            property_analysis.processing_stage = 'failed'
            property_analysis.save()
            
            error_msg = f"AI analysis failed for property {property_analysis_id}: {result.get('message', 'Unknown error')}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except PropertyAnalysis.DoesNotExist:
        logger.error(f"Property analysis {property_analysis_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error analyzing property {property_analysis_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            raise

@shared_task
def batch_analyze_pending_properties():
    """Analyze all pending properties in batches"""
    pending_properties = PropertyAnalysis.objects.filter(status='analyzing')[:50]  # Limit batch size
    
    for prop in pending_properties:
        analyze_property_task.delay(prop.id)
    
    return f"Queued analysis for {pending_properties.count()} properties"

# apps/property_ai/tasks.py (add to your existing tasks.py)

@shared_task
def daily_property_scrape():
    """Daily scraping task for new properties"""
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    
    # Get the first superuser or create a system user
    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    
    if not system_user:
        logger.error("No superuser found for daily scraping")
        return "Error: No superuser found"
    
    try:
        # Run scraping with analysis
        call_command(
            'scrape_century21_sales',
            f'--user-id={system_user.id}',
            '--max-pages=10',  # Fewer pages for daily updates
            '--analyze',
            '--batch-size=15',
            '--delay=2.5'
        )
        
        # Also analyze any pending properties
        batch_analyze_pending_properties.delay()
        
        logger.info("Daily property scrape completed successfully")
        return "Daily scrape completed"
        
    except Exception as e:
        logger.error(f"Daily property scrape failed: {e}")
        return f"Daily scrape failed: {e}"