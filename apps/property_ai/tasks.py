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
from .analytics import PropertyAnalytics

from django.contrib.auth import get_user_model
from django.db.models import Q, Avg
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
        
        # Filter to only NEW URLs (URLs are already standardized from scraper)
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
                    
                time.sleep(4)  # More respectful delay for daily scraping
                
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
        
        # More conservative page limits for safety
        if current_count < 200:  # Initial building phase
            pages_to_scrape = 40  # Reduced from 35
        elif current_count < 500:  # Growth phase
            pages_to_scrape = 30  # Reduced from 30
        elif current_count < 1000:  # Expansion phase
            pages_to_scrape = 20  # Reduced from 25
        else:  # Maintenance phase - just check for new properties
            pages_to_scrape = 15  # Reduced from 20
        
        # Additional safety check - don't scrape if we've done too much recently
        recent_scrapes = PropertyAnalysis.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=6)
        ).count()
        
        if recent_scrapes > 300:
            logger.warning(f"⚠️ Too many recent scrapes ({recent_scrapes}), skipping midnight scrape")
            return {
                'status': 'skipped',
                'reason': f'Too many recent scrapes: {recent_scrapes}',
                'recent_scrapes': recent_scrapes
            }
        
        logger.info(f"🌙 Midnight scrape starting: {pages_to_scrape} pages from page {start_page}")
        logger.info(f"📊 Current database: {current_count} properties")
        logger.info(f"🕐 Recent scrapes (6h): {recent_scrapes}")
        
        # Track start time and count for reporting
        start_time = timezone.now()
        initial_count = current_count
        
        # Run the bulletproof scraper with proper resumption
        call_command(
            'bulk_scrape_initial',
            f'--user-id={system_user.id}',
            f'--max-pages={pages_to_scrape}',
            f'--start-page={start_page}',
            '--delay=6.0',  # Safer overnight delay
            '--ultra-safe'  # Enable maximum safety for overnight
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

@shared_task
def send_property_alerts_task():
    """Send email alerts to users about new properties that are good deals"""
    try:
        User = get_user_model()
        analytics = PropertyAnalytics()
        
        # Get properties added in the last 24 hours
        yesterday = timezone.now() - timezone.timedelta(days=1)
        new_properties = PropertyAnalysis.objects.filter(
            created_at__gte=yesterday,
            scraped_by__isnull=False,  # Only system-scraped properties
            user__isnull=True,  # Not user-requested analyses
            asking_price__gt=0  # Must have a valid price
        ).order_by('-created_at')
        
        if not new_properties.exists():
            logger.info("No new properties found for alerts")
            return "No new properties found"
        
        # Get users who want property alerts
        users_with_alerts = User.objects.filter(
            profile__email_property_alerts=True,
            profile__is_email_verified=True,
            is_active=True
        ).select_related('profile')
        
        if not users_with_alerts.exists():
            logger.info("No users with property alerts enabled")
            return "No users with alerts enabled"
        
        # Group properties by location for efficient processing
        properties_by_location = {}
        for prop in new_properties:
            location = prop.property_location.split(',')[0].strip()
            if location not in properties_by_location:
                properties_by_location[location] = []
            properties_by_location[location].append(prop)
        
        # Get market stats for each location
        location_market_stats = {}
        for location in properties_by_location.keys():
            market_stats = analytics.get_location_market_stats(location)
            if market_stats and market_stats.get('avg_price'):
                location_market_stats[location] = market_stats
        
        # Find properties that are at least 10% below market average
        good_deals = []
        for location, properties in properties_by_location.items():
            if location not in location_market_stats:
                continue
                
            avg_price = location_market_stats[location]['avg_price']
            for prop in properties:
                if prop.asking_price and avg_price:
                    price_discount = ((avg_price - prop.asking_price) / avg_price) * 100
                    if price_discount >= 10:  # At least 10% below average
                        good_deals.append({
                            'property': prop,
                            'location': location,
                            'price_discount': price_discount,
                            'market_stats': location_market_stats[location]
                        })
        
        if not good_deals:
            logger.info("No properties found that are 10%+ below market average")
            return "No good deals found"
        
        # Send alerts to users
        alerts_sent = 0
        for user in users_with_alerts:
            try:
                # Filter deals based on user preferences
                user_deals = []
                for deal in good_deals:
                    if user.profile.should_receive_property_alert(deal['property']):
                        user_deals.append(deal)
                
                if user_deals:
                    # Send email alert
                    send_property_alert_email.delay(user.id, [deal['property'].id for deal in user_deals])
                    alerts_sent += 1
                    
            except Exception as e:
                logger.error(f"Error processing alerts for user {user.id}: {e}")
                continue
        
        logger.info(f"Property alerts task completed: {alerts_sent} users notified about {len(good_deals)} good deals")
        return f"Sent {alerts_sent} property alerts"
        
    except Exception as e:
        logger.error(f"Error in property alerts task: {e}")
        return f"Property alerts task failed: {e}"

@shared_task
def send_property_alert_email(user_id, property_ids):
    """Send property alert email to a specific user"""
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        properties = PropertyAnalysis.objects.filter(id__in=property_ids)
        
        if not properties.exists():
            return f"No properties found for user {user_id}"
        
        # Prepare email context
        context = {
            'user': user,
            'properties': properties,
            'property_count': properties.count(),
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://propertyai.com'
        }
        
        # Render email templates
        subject = f"🏠 {properties.count()} New Property Deal{'s' if properties.count() > 1 else ''} Found!"
        
        html_message = render_to_string('property_ai/emails/property_alert.html', context)
        text_message = render_to_string('property_ai/emails/property_alert.txt', context)
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        
        logger.info(f"Sent property alert email to {user.email} for {properties.count()} properties")
        return f"Alert sent to {user.email}"
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for property alert")
        return f"User {user_id} not found"
    except Exception as e:
        logger.error(f"Error sending property alert email to user {user_id}: {e}")
        return f"Error sending alert: {e}"