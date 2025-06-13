import time
from functools import wraps
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def monitor_db_queries(func):
    """Decorator to monitor database query performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if settings.DEBUG:
            initial_queries = len(connection.queries)
            start_time = time.time()
            
            result = func(*args, **kwargs)
            
            end_time = time.time()
            execution_time = end_time - start_time
            query_count = len(connection.queries) - initial_queries
            
            logger.info(f"{func.__name__}: {execution_time:.2f}s, {query_count} queries")
            
            return result
        else:
            return func(*args, **kwargs)
    return wrapper

def monitor_performance(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
        
        return result
    return wrapper