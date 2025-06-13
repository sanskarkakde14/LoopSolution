from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('uptime_monitor', '0002_businesshours_uptime_moni_store_i_936a75_idx_and_more'),
    ]

    operations = [
        # Enable pg_trgm extension for text search
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            "DROP EXTENSION IF EXISTS pg_trgm;"
        ),
        # Add PostgreSQL-specific indexes
        migrations.RunSQL(
            # Create partial indexes for active/inactive status
            """
            CREATE INDEX IF NOT EXISTS store_status_active_idx 
            ON uptime_monitor_storestatus (store_id, timestamp_utc) 
            WHERE status = 'active';
            
            CREATE INDEX IF NOT EXISTS store_status_inactive_idx 
            ON uptime_monitor_storestatus (store_id, timestamp_utc) 
            WHERE status = 'inactive';
            
            -- Create BRIN index for timestamp (good for time-series data)
            CREATE INDEX IF NOT EXISTS store_status_timestamp_brin_idx 
            ON uptime_monitor_storestatus USING BRIN (timestamp_utc);
            
            -- Create GIN index for store_id (good for exact matches)
            CREATE INDEX IF NOT EXISTS store_id_gin_idx 
            ON uptime_monitor_store USING GIN (store_id gin_trgm_ops);
            
            -- Create GiST index for timezone_str (good for text search)
            CREATE INDEX IF NOT EXISTS timezone_str_gist_idx 
            ON uptime_monitor_store USING GIST (timezone_str gist_trgm_ops);
            """,
            # Revert changes
            """
            DROP INDEX IF EXISTS store_status_active_idx;
            DROP INDEX IF EXISTS store_status_inactive_idx;
            DROP INDEX IF EXISTS store_status_timestamp_brin_idx;
            DROP INDEX IF EXISTS store_id_gin_idx;
            DROP INDEX IF EXISTS timezone_str_gist_idx;
            """
        ),
    ] 