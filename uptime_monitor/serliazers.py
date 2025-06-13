
from rest_framework import serializers
from .models import Report, Store

class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model"""
    class Meta:
        model = Report
        fields = ['report_id', 'status', 'created_at', 'completed_at']

class StoreUptimeSerializer(serializers.Serializer):
    """Serializer for store uptime data"""
    store_id = serializers.CharField()
    uptime_last_hour = serializers.FloatField()
    uptime_last_day = serializers.FloatField()
    uptime_last_week = serializers.FloatField()
    downtime_last_hour = serializers.FloatField()
    downtime_last_day = serializers.FloatField()
    downtime_last_week = serializers.FloatField()