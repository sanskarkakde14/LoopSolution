import pandas as pd
import pytz
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import os
import threading
from .models import Store, StoreStatus, BusinessHours, Report
import logging
from django.db import models

logger = logging.getLogger(__name__)

class UptimeCalculationService:
    """Service for calculating store uptime/downtime metrics"""
    
    def __init__(self):
        self.current_timestamp = self._get_current_timestamp()
    
    def _get_current_timestamp(self):
        """Get the maximum timestamp from store_status as current time"""
        max_timestamp = StoreStatus.objects.aggregate(
            max_time=models.Max('timestamp_utc')
        )['max_time']
        
        if max_timestamp:
            return max_timestamp.replace(tzinfo=pytz.UTC)
        return timezone.now()
    
    def calculate_store_uptime(self, store_id: str):
        """Calculate uptime metrics for a specific store"""
        try:
            store = Store.objects.get(store_id=store_id)
            store_tz = pytz.timezone(store.timezone_str)
            current_local = self.current_timestamp.astimezone(store_tz)
            
            # Calculate metrics for different time periods
            metrics = {}
            
            # Last hour metrics
            metrics.update(self._calculate_period_metrics(store, current_local, 'hour', 1))
            
            # Last day metrics
            metrics.update(self._calculate_period_metrics(store, current_local, 'day', 1))
            
            # Last week metrics
            metrics.update(self._calculate_period_metrics(store, current_local, 'week', 1))
            
            return metrics
            
        except Store.DoesNotExist:
            logger.error(f"Store {store_id} not found")
            return {}
        except Exception as e:
            logger.error(f"Error calculating uptime for store {store_id}: {str(e)}")
            return {}
    
    def _calculate_period_metrics(self, store, current_local, period_type, period_count):
        """Calculate metrics for a specific time period"""
        
        # Determine the start time for the period
        if period_type == 'hour':
            start_time = current_local - timedelta(hours=period_count)
        elif period_type == 'day':
            start_time = current_local - timedelta(days=period_count)
        elif period_type == 'week':
            start_time = current_local - timedelta(weeks=period_count)
        else:
            raise ValueError(f"Invalid period_type: {period_type}")
        
        # Get business hours for the period
        business_periods = self._get_business_periods(store, start_time, current_local)
        
        if not business_periods:
            # Store is 24/7 or no business hours defined
            business_periods = [(start_time, current_local)]
        
        total_uptime = 0
        total_business_time = 0
        
        # Optimize status query by getting all statuses for the period at once
        period_start_utc = start_time.astimezone(pytz.UTC)
        period_end_utc = current_local.astimezone(pytz.UTC)
        
        status_logs = StoreStatus.objects.filter(
            store=store,
            timestamp_utc__gte=period_start_utc,
            timestamp_utc__lte=period_end_utc
        ).order_by('timestamp_utc').values_list('timestamp_utc', 'status')
        
        # Convert to list for faster iteration
        status_logs = list(status_logs)
        
        for period_start, period_end in business_periods:
            # Convert to UTC for calculations
            period_start_utc = period_start.astimezone(pytz.UTC)
            period_end_utc = period_end.astimezone(pytz.UTC)
            
            # Calculate uptime for this business period
            period_uptime, period_duration = self._interpolate_uptime(
                status_logs, period_start_utc, period_end_utc
            )
            
            total_uptime += period_uptime
            total_business_time += period_duration
        
        # Convert to appropriate units
        if period_type == 'hour':
            uptime_key = 'uptime_last_hour'
            downtime_key = 'downtime_last_hour'
            # Convert to minutes
            total_uptime_units = total_uptime / 60
            total_downtime_units = (total_business_time - total_uptime) / 60
        else:
            uptime_key = f'uptime_last_{period_type}'
            downtime_key = f'downtime_last_{period_type}'
            # Convert to hours
            total_uptime_units = total_uptime / 3600
            total_downtime_units = (total_business_time - total_uptime) / 3600
        
        return {
            uptime_key: max(0, total_uptime_units),
            downtime_key: max(0, total_downtime_units)
        }
    
    def _get_business_periods(self, store, start_time, end_time):
        """Get all business periods within the given time range"""
        
        # Optimize query by getting all business hours at once
        business_hours = BusinessHours.objects.filter(store=store)
        
        if not business_hours:
            # Store is 24/7
            return [(start_time, end_time)]
        
        periods = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            
            business_hour = business_hours.filter(day_of_week=day_of_week).first()
            
            if business_hour:
                period_start = datetime.combine(current_date, business_hour.start_time_local)
                period_end = datetime.combine(current_date, business_hour.end_time_local)
                
                # Add timezone info
                store_tz = pytz.timezone(store.timezone_str)
                period_start = store_tz.localize(period_start)
                period_end = store_tz.localize(period_end)
                
                # Handle overnight business hours
                if business_hour.end_time_local < business_hour.start_time_local:
                    period_end += timedelta(days=1)
                
                # Clip to our target range
                period_start = max(period_start, start_time)
                period_end = min(period_end, end_time)
                
                if period_start < period_end:
                    periods.append((period_start, period_end))
            
            current_date += timedelta(days=1)
        
        return periods
    
    def _interpolate_uptime(self, status_logs, start_time, end_time):
        """Calculate uptime by interpolating between status logs"""
        
        if not status_logs:
            return 0, 0
        
        total_duration = (end_time - start_time).total_seconds()
        if total_duration <= 0:
            return 0, 0
        
        # Add start and end points if they don't exist
        if status_logs[0][0] > start_time:
            status_logs.insert(0, (start_time, 'inactive'))
        if status_logs[-1][0] < end_time:
            status_logs.append((end_time, 'inactive'))
        
        uptime = 0
        current_time = start_time
        
        for i in range(len(status_logs) - 1):
            timestamp, status = status_logs[i]
            next_timestamp = status_logs[i + 1][0]
            
            if timestamp >= end_time:
                break
                
            if current_time < timestamp:
                # Gap between current time and next status
                uptime += 0  # Assume inactive during gaps
                current_time = timestamp
            
            if status == 'active':
                period_end = min(next_timestamp, end_time)
                uptime += (period_end - current_time).total_seconds()
            
            current_time = next_timestamp
        
        return uptime, total_duration

class ReportGenerationService:
    """Service for background report generation"""
    
    def __init__(self):
        self.uptime_service = UptimeCalculationService()
    
    def generate_report_async(self, report_id: str):
        """Generate report in background thread"""
        def _generate():
            try:
                self._generate_report(report_id)
            except Exception as e:
                logger.error(f"Report generation failed for {report_id}: {str(e)}")
                self._mark_report_failed(report_id, str(e))
        
        thread = threading.Thread(target=_generate)
        thread.daemon = True
        thread.start()
    
    def _generate_report(self, report_id: str):
        """Generate the actual report"""
        try:
            report = Report.objects.get(report_id=report_id)
            stores = Store.objects.all()
            
            data = []
            for store in stores:
                metrics = self.uptime_service.calculate_store_uptime(store.store_id)
                if metrics:
                    data.append({
                        'store_id': store.store_id,
                        **metrics
                    })
            
            df = pd.DataFrame(data)
            
            # Create reports directory if it doesn't exist
            reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Save report
            file_path = f'reports/report_{report_id}.csv'
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            df.to_csv(full_path, index=False)
            
            # Update report status
            report.status = 'Complete'
            report.file_path = file_path
            report.completed_at = timezone.now()
            report.save()
            
        except Exception as e:
            logger.error(f"Error generating report {report_id}: {str(e)}")
            self._mark_report_failed(report_id, str(e))
            raise
    
    def _mark_report_failed(self, report_id: str, error_message: str):
        """Mark a report as failed with error message"""
        try:
            report = Report.objects.get(report_id=report_id)
            report.status = 'Failed'
            report.error_message = error_message
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error marking report {report_id} as failed: {str(e)}")