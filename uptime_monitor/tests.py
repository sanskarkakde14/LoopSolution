from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, time, timedelta
import pytz
import json
from unittest.mock import patch, MagicMock
from .models import Store, StoreStatus, BusinessHours, Report
from .services import UptimeCalculationService, ReportGenerationService

class UptimeCalculationServiceTest(TestCase):
    """Test cases for uptime calculation logic"""
    
    def setUp(self):
        """Set up test data"""
        self.store = Store.objects.create(
            store_id='test_store_1',
            timezone_str='America/New_York'
        )
        
        # Create business hours (9 AM - 5 PM, Monday to Friday)
        for day in range(5):  # Monday to Friday
            BusinessHours.objects.create(
                store=self.store,
                day_of_week=day,
                start_time_local=time(9, 0),
                end_time_local=time(17, 0)
            )
        
        self.service = UptimeCalculationService()
    
    def test_calculate_uptime_with_full_active_period(self):
        """Test uptime calculation when store is fully active"""
        # Mock current time
        current_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)  # Monday noon
        
        with patch.object(self.service, '_get_current_timestamp', return_value=current_time):
            # Create status logs showing store was active
            StoreStatus.objects.create(
                store=self.store,
                timestamp_utc=current_time - timedelta(hours=2),
                status='active'
            )
            
            metrics = self.service.calculate_store_uptime('test_store_1')
            
            # Store should have some uptime during business hours
            self.assertGreater(metrics['uptime_last_hour'], 0)
            self.assertGreater(metrics['uptime_last_day'], 0)
    
    def test_calculate_uptime_with_mixed_status(self):
        """Test uptime calculation with mixed active/inactive periods"""
        current_time = datetime(2024, 1, 15, 15, 0, 0, tzinfo=pytz.UTC)  # Monday 3 PM
        
        with patch.object(self.service, '_get_current_timestamp', return_value=current_time):
            # Create mixed status logs
            base_time = current_time - timedelta(hours=4)
            
            StoreStatus.objects.create(store=self.store, timestamp_utc=base_time, status='active')
            StoreStatus.objects.create(store=self.store, timestamp_utc=base_time + timedelta(hours=1), status='inactive')
            StoreStatus.objects.create(store=self.store, timestamp_utc=base_time + timedelta(hours=2), status='active')
            
            metrics = self.service.calculate_store_uptime('test_store_1')
            
            # Should have both uptime and downtime
            self.assertGreater(metrics['uptime_last_day'], 0)
            self.assertGreater(metrics['downtime_last_day'], 0)
    
    def test_store_with_24_7_operation(self):
        """Test store with no business hours (24/7 operation)"""
        store_24_7 = Store.objects.create(
            store_id='store_24_7',
            timezone_str='America/Chicago'
        )
        
        current_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
        
        with patch.object(self.service, '_get_current_timestamp', return_value=current_time):
            StoreStatus.objects.create(
                store=store_24_7,
                timestamp_utc=current_time - timedelta(hours=1),
                status='active'
            )
            
            metrics = self.service.calculate_store_uptime('store_24_7')
            
            # Should have 60 minutes of uptime in last hour
            self.assertAlmostEqual(metrics['uptime_last_hour'], 60, delta=1)

class APIEndpointsTest(TestCase):
    """Test cases for API endpoints"""
    
    def setUp(self):
        self.client = Client()
        
        # Create test store
        self.store = Store.objects.create(
            store_id='api_test_store',
            timezone_str='America/Los_Angeles'
        )
    
    def test_trigger_report_endpoint(self):
        """Test the trigger_report API endpoint"""
        response = self.client.post('/api/trigger_report')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('report_id', data)
        
        # Verify report was created in database
        report_id = data['report_id']
        report = Report.objects.get(report_id=report_id)
        self.assertEqual(report.status, 'Running')
    
    def test_get_report_endpoint_running(self):
        """Test get_report endpoint for running report"""
        report = Report.objects.create(status='Running')
        
        response = self.client.get(f'/api/get_report/{report.report_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'Running')
    
    def test_get_report_endpoint_complete(self):
        """Test get_report endpoint for completed report"""
        report = Report.objects.create(
            status='Complete',
            file_path='reports/test_report.csv'
        )
        
        response = self.client.get(f'/api/get_report/{report.report_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'Complete')
        self.assertIn('file', data)
    
    def test_get_report_endpoint_not_found(self):
        """Test get_report endpoint for non-existent report"""
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        response = self.client.get(f'/api/get_report/{fake_uuid}')
        
        self.assertEqual(response.status_code, 404)