from django.db import models
import uuid

class Store(models.Model):
    store_id = models.CharField(max_length=100, unique=True, primary_key=True)
    timezone_str = models.CharField(max_length=50, default='America/Chicago')
    
    def __str__(self):
        return f"Store {self.store_id}"

class StoreStatus(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='statuses')
    timestamp_utc = models.DateTimeField()
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')])
    
    def __str__(self):
        return f"{self.store.store_id} - {self.status} at {self.timestamp_utc}"

class BusinessHours(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='business_hours')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time_local = models.TimeField()
    end_time_local = models.TimeField()
    
    def __str__(self):
        return f"{self.store.store_id} - {self.get_day_of_week_display()}: {self.start_time_local}-{self.end_time_local}"

class Report(models.Model):
    STATUS_CHOICES = [
        ('Running', 'Running'),
        ('Complete', 'Complete'),
        ('Failed', 'Failed'),
    ]
    
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Running')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Report {self.report_id} - {self.status}"