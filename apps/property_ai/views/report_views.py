# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from ..models import PropertyAnalysis
import logging
from django.http import FileResponse
import os
from django.utils import timezone


logger = logging.getLogger(__name__)

@login_required
def download_report(request, analysis_id):
    """Download PDF report"""
    analysis = get_object_or_404(PropertyAnalysis, id=analysis_id, user=request.user)
    
    if analysis.report_generated and analysis.report_file_path:
        if os.path.exists(analysis.report_file_path):
            # Create a professional filename
            property_title = analysis.property_title or "Property"
            safe_title = "".join(c for c in property_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')[:30]  # Limit length
            
            filename = f"AI_Property_Analysis_{safe_title}_{analysis_id[:8]}.pdf"
            
            return FileResponse(
                open(analysis.report_file_path, 'rb'),
                as_attachment=True,
                filename=filename
            )
    
    messages.error(request, 'Report not available for download.')
    return redirect('property_ai:analysis_detail', analysis_id=analysis_id)