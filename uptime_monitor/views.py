from datetime import timedelta
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse
import json
import os
from loguru import logger
from .models import *
from .services import ReportGenerationService
from django.utils import timezone
import pandas as pd
from django.db import transaction

@csrf_exempt
@require_http_methods(["POST"])
def trigger_report(request):
    try:
        # Check if there's a recent report still running
        recent_running = Report.objects.filter(
            status='Running',
            created_at__gte=timezone.now() - timedelta(minutes=30)
        ).first()
        
        if recent_running:
            return JsonResponse({
                'report_id': str(recent_running.report_id),
                'message': 'Using existing running report'
            })
        
        # Create new report record
        report = Report.objects.create()
        
        # Start background report generation
        report_service = ReportGenerationService()
        report_service.generate_report_async(str(report.report_id))
        
        return JsonResponse({
            'report_id': str(report.report_id),
            'estimated_completion': '2-5 minutes'
        })
        
    except Exception as e:
        logger.error(f"Error triggering report: {str(e)}")
        return JsonResponse({
            'error': 'Failed to trigger report generation',
            'details': str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_report(request, report_id):
    try:
        report = Report.objects.get(report_id=report_id)
        
        response_data = {'status': report.status}
        
        if report.status == 'Complete':
            file_url = request.build_absolute_uri(
                settings.MEDIA_URL + report.file_path
            )
            response_data.update({
                'file': file_url,
                'completed_at': report.completed_at.isoformat(),
                'file_size': _get_file_size(report.file_path)
            })
            
        elif report.status == 'Failed':
            response_data.update({
                'error': report.error_message or 'Report generation failed',
                'failed_at': report.completed_at.isoformat() if report.completed_at else None
            })
            
        elif report.status == 'Running':
            elapsed = (timezone.now() - report.created_at).total_seconds()
            estimated_progress = min(int((elapsed / 300) * 100), 95)  # 5 min estimate
            response_data['progress'] = f"{estimated_progress}%"
        
        return JsonResponse(response_data)
            
    except Report.DoesNotExist:
        raise Http404("Report not found")
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to retrieve report status',
            'details': str(e)
        }, status=500)

def _get_file_size(file_path):
    try:
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        size_bytes = os.path.getsize(full_path)
        return f"{size_bytes / (1024*1024):.2f} MB"
    except:
        return "Unknown"

@csrf_exempt
@require_http_methods(["POST"])
def upload_excel(request):
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
            
        excel_file = request.FILES['file']
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            return JsonResponse({'error': 'Invalid file format'}, status=400)
            
        # Create a temporary file to store the uploaded Excel
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', excel_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)
        
        # Process the Excel file
        df = pd.read_excel(temp_path)
        
        with transaction.atomic():
            # Process stores
            store_data = df[['store_id']].drop_duplicates()
            store_data['timezone_str'] = 'America/Chicago'
            Store.objects.bulk_create(
                [Store(**row) for _, row in store_data.iterrows()],
                ignore_conflicts=True
            )
            
            # Process status records
            if 'timestamp_utc' in df.columns and 'status' in df.columns:
                df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
                status_data = df[['store_id', 'timestamp_utc', 'status']].drop_duplicates()
                StoreStatus.objects.bulk_create(
                    [StoreStatus(**row) for _, row in status_data.iterrows()],
                    ignore_conflicts=True
                )
            
            # Process business hours
            if all(k in df.columns for k in ['day_of_week', 'start_time_local', 'end_time_local']):
                business_hours_data = df[['store_id', 'day_of_week', 'start_time_local', 'end_time_local']].drop_duplicates()
                BusinessHours.objects.bulk_create(
                    [BusinessHours(**row) for _, row in business_hours_data.iterrows()],
                    ignore_conflicts=True
                )
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return JsonResponse({
            'message': 'File processed successfully',
            'total_rows': len(df)
        })
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        return JsonResponse({
            'error': 'Failed to process Excel file',
            'details': str(e)
        }, status=500)