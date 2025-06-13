from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
import pytz
from datetime import datetime
from uptime_monitor.models import Store, StoreStatus, BusinessHours
import os

class Command(BaseCommand):
    help = 'Load data from CSV files'

    def add_arguments(self, parser):
        parser.add_argument('csv_directory', type=str, help='Directory containing CSV files')

    def handle(self, *args, **options):
        csv_dir = options['csv_directory']
        
        self.stdout.write('Starting CSV data import...')
        
        try:
            with transaction.atomic():
                # Load store timezones
                self.load_store_timezones(csv_dir)
                
                # Load business hours
                self.load_business_hours(csv_dir)
                
                # Load store status
                self.load_store_status(csv_dir)
                
            self.stdout.write(
                self.style.SUCCESS('Successfully imported all CSV data')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error importing CSV data: {str(e)}')
            )
            raise

    def load_store_timezones(self, csv_dir):
        """Load store timezone data"""
        file_path = os.path.join(csv_dir, 'timezones.csv')
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                Store.objects.update_or_create(
                    store_id=row['store_id'],
                    defaults={'timezone_str': row['timezone_str']}
                )
            
            self.stdout.write(f'Loaded {len(df)} store timezones')
        else:
            self.stdout.write('timezones.csv not found, skipping...')

    def load_business_hours(self, csv_dir):
        """Load business hours data"""
        file_path = os.path.join(csv_dir, 'menu_hours.csv')
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                store, _ = Store.objects.get_or_create(
                    store_id=row['store_id'],
                    defaults={'timezone_str': 'America/Chicago'}
                )
                
                BusinessHours.objects.update_or_create(
                    store=store,
                    day_of_week=row['dayOfWeek'],
                    defaults={
                        'start_time_local': row['start_time_local'],
                        'end_time_local': row['end_time_local']
                    }
                )
            
            self.stdout.write(f'Loaded {len(df)} business hour records')
        else:
            self.stdout.write('menu_hours.csv not found, skipping...')

    def load_store_status(self, csv_dir):
        """Load store status data"""
        file_path = os.path.join(csv_dir, 'store_status.csv')
        
        if not os.path.exists(file_path):
            raise FileNotFoundError('store_status.csv is required')
        
        df = pd.read_csv(file_path)
        
        # Convert timestamp to datetime
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
        
        batch_size = 1000
        created_count = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            status_objects = []
            
            for _, row in batch.iterrows():
                store, _ = Store.objects.get_or_create(
                    store_id=row['store_id'],
                    defaults={'timezone_str': 'America/Chicago'}
                )
                
                status_objects.append(
                    StoreStatus(
                        store=store,
                        timestamp_utc=row['timestamp_utc'],
                        status=row['status']
                    )
                )
            
            # Bulk create with ignore conflicts
            StoreStatus.objects.bulk_create(
                status_objects, 
                ignore_conflicts=True,
                batch_size=batch_size
            )
            created_count += len(status_objects)
            
            if i % (batch_size * 10) == 0:
                self.stdout.write(f'Processed {i}/{len(df)} status records...')
        
        self.stdout.write(f'Loaded {created_count} store status records')