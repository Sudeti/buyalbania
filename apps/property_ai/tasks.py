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

            'agent_name': property_analysis.agent_name,
            'agent_email': property_analysis.agent_email,
            'agent_phone': property_analysis.agent_phone,
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
def daily_property_scrape():
    """Lightweight daily scraping for NEW properties only"""
    from django.contrib.auth import get_user_model
    from apps.property_ai.scrapers import Century21AlbaniaScraper
    
    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    
    if not system_user:
        logger.error("No superuser found for daily scraping")
        return "Error: No superuser found"
    
    try:
        scraper = Century21AlbaniaScraper()
        
        # Only check first 5 pages for new properties
        urls = scraper.get_sale_property_listings(max_pages=5)
        
        # Filter to only NEW URLs
        existing_urls = set(PropertyAnalysis.objects.values_list('property_url', flat=True))
        new_urls = [url for url in urls if url not in existing_urls]
        
        if not new_urls:
            logger.info("No new properties found in daily check")
            return "No new properties found"
        
        # Scrape only the new ones
        new_count = 0
        for url in new_urls[:20]:  # Limit to 20 new properties per day
            try:
                data = scraper.scrape_property(url)
                if data and data['price'] > 0:
                    PropertyAnalysis.objects.create(
                        user=None,
                        scraped_by=system_user,
                        property_url=data['url'],
                        property_title=data['title'],
                        property_location=data['location'],
                        neighborhood=data.get('neighborhood', ''),
                        asking_price=data['price'],
                        property_type=data['property_type'],
                        total_area=data['square_meters'],
                        property_condition=data['condition'],
                        floor_level=data['floor_level'],
                        agent_name=data.get('agent_name', ''),
                        agent_email=data.get('agent_email', ''),
                        agent_phone=data.get('agent_phone', ''),
                        status='analyzing'
                    )
                    new_count += 1
                    
                    # Queue for analysis
                    analyze_property_task.delay(PropertyAnalysis.objects.latest('created_at').id)
                    
                time.sleep(2)  # Respectful delay
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        logger.info(f"Daily scrape completed: {new_count} new properties")
        return f"Added {new_count} new properties"
        
    except Exception as e:
        logger.error(f"Daily property scrape failed: {e}")
        return f"Daily scrape failed: {e}"

@shared_task
def midnight_bulk_scrape_task():
    """Safe midnight bulk scraping with proper resumption"""
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from apps.property_ai.management.commands.bulk_scrape_initial import Command
    
    try:
        User = get_user_model()
        system_user = User.objects.filter(is_superuser=True).first()
        
        if not system_user:
            logger.error("No superuser found for midnight scraping")
            return "Error: No superuser found"
        
        # FIXED: Use the proper resume calculation
        command_instance = Command()
        start_page = command_instance.calculate_resume_page()
        
        # Determine pages to scrape based on current database size
        current_count = PropertyAnalysis.objects.count()
        
        if current_count < 200:  # Initial building phase
            pages_to_scrape = 25
        elif current_count < 500:  # Growth phase
            pages_to_scrape = 20
        elif current_count < 1000:  # Expansion phase
            pages_to_scrape = 15
        else:  # Maintenance phase - just check for new properties
            pages_to_scrape = 10
        
        logger.info(f"🌙 Midnight scrape starting: {pages_to_scrape} pages from page {start_page}")
        logger.info(f"📊 Current database: {current_count} properties")
        
        # Track start time and count for reporting
        start_time = timezone.now()
        initial_count = current_count
        
        # Run the bulletproof scraper with proper resumption
        call_command(
            'bulk_scrape_initial',
            f'--user-id={system_user.id}',
            f'--max-pages={pages_to_scrape}',
            f'--start-page={start_page}',
            '--delay=2.5'  # Faster at night when less traffic
        )
        
        # Calculate results
        end_time = timezone.now()
        final_count = PropertyAnalysis.objects.count()
        scraped_this_run = final_count - initial_count
        duration = (end_time - start_time).total_seconds() / 60  # minutes
        
        # Log comprehensive results
        logger.info(f"🎉 Midnight scrape completed successfully!")
        logger.info(f"⏱️ Duration: {duration:.1f} minutes")
        logger.info(f"📈 New properties: {scraped_this_run}")
        logger.info(f"📊 Total database: {final_count} properties")
        logger.info(f"🔄 Next run will start from page ~{start_page + pages_to_scrape}")
        
        return {
            'status': 'success',
            'new_properties': scraped_this_run,
            'total_properties': final_count,
            'duration_minutes': round(duration, 1),
            'pages_scraped': pages_to_scrape,
            'next_start_page': start_page + pages_to_scrape
        }
        
    except Exception as e:
        logger.error(f"❌ Midnight scrape failed: {e}")
        
        # Try to provide helpful error context
        try:
            current_count = PropertyAnalysis.objects.count()
            logger.error(f"📊 Database state at failure: {current_count} properties")
        except:
            pass
            
        return f"Midnight scrape failed: {e}"