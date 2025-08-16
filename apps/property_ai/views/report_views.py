# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.conf import settings
from ..models import PropertyAnalysis
import logging
from django.http import FileResponse
import os
from django.utils import timezone


logger = logging.getLogger(__name__)

@login_required
def download_report(request, analysis_id):
    """Download PDF report"""
    try:
        # First try to get the analysis without user filter
        analysis = get_object_or_404(PropertyAnalysis, id=analysis_id)
        
        # Check if user has access to this analysis
        if not analysis.is_available_to_user(request.user):
            logger.warning(f"User {request.user.id} ({request.user.email}) denied access to analysis {analysis_id}")
            logger.warning(f"Analysis user: {analysis.user}, Analysis status: {analysis.status}")
            if hasattr(request.user, 'profile'):
                logger.warning(f"User profile tier: {request.user.profile.subscription_tier}")
            else:
                logger.warning("User has no profile")
            messages.error(request, 'You do not have access to this analysis.')
            return redirect('property_ai:my_analyses')
        
        if analysis.report_generated and analysis.report_file_path:
            logger.info(f"Checking report file: {analysis.report_file_path}")
            logger.info(f"File exists: {os.path.exists(analysis.report_file_path)}")
            
            if os.path.exists(analysis.report_file_path):
                # Create a professional filename
                property_title = analysis.property_title or "Property"
                safe_title = "".join(c for c in property_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_')[:30]  # Limit length
                
                filename = f"AI_Property_Analysis_{safe_title}_{analysis_id[:8]}.pdf"
                
                try:
                    return FileResponse(
                        open(analysis.report_file_path, 'rb'),
                        as_attachment=True,
                        filename=filename
                    )
                except Exception as e:
                    logger.error(f"Error opening file {analysis.report_file_path}: {e}")
                    messages.error(request, 'Error reading report file.')
                    return redirect('property_ai:analysis_detail', analysis_id=analysis_id)
            else:
                logger.error(f"Report file not found at path: {analysis.report_file_path}")
                logger.error(f"Current working directory: {os.getcwd()}")
                logger.error(f"MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', 'Not set')}")
                messages.error(request, 'Report file not found on server.')
        else:
            logger.warning(f"Analysis {analysis_id} has report_generated={analysis.report_generated}, report_file_path={analysis.report_file_path}")
            messages.error(request, 'Report not available for download.')
        
        return redirect('property_ai:analysis_detail', analysis_id=analysis_id)
        
    except Exception as e:
        logger.error(f"Error downloading report for analysis {analysis_id}: {e}")
        messages.error(request, 'Error accessing report. Please try again.')
        return redirect('property_ai:my_analyses')