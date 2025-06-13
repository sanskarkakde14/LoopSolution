from django.contrib import admin
from .models import Store, StoreStatus, BusinessHours, Report

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('store_id', 'timezone_str')
    search_fields = ('store_id',)

@admin.register(StoreStatus)
class StoreStatusAdmin(admin.ModelAdmin):
    list_display = ('store', 'timestamp_utc', 'status')
    list_filter = ('status', 'timestamp_utc')
    search_fields = ('store__store_id',)

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ('store', 'day_of_week', 'start_time_local', 'end_time_local')
    list_filter = ('day_of_week',)
    search_fields = ('store__store_id',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_id', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('report_id', 'created_at')
