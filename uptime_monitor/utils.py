from loguru import logger
from typing import Dict, Any
from datetime import datetime
import pytz


def validate_timezone(timezone_str: str) -> bool:
    """Validate if timezone string is valid"""
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def convert_utc_to_local(utc_datetime: datetime, timezone_str: str) -> datetime:
    """Convert UTC datetime to local timezone"""
    try:
        utc_tz = pytz.UTC
        local_tz = pytz.timezone(timezone_str)
        
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_tz.localize(utc_datetime)
        
        return utc_datetime.astimezone(local_tz)
    except Exception as e:
        logger.error(f"Error converting timezone: {str(e)}")
        return utc_datetime

def log_performance_metrics(func_name: str, execution_time: float, **kwargs):
    """Log performance metrics for monitoring"""
    logger.info(f"Performance: {func_name} took {execution_time:.2f}s", extra=kwargs)
