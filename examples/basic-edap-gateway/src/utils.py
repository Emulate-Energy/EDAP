"""Some utility functions, mostly for logging."""
import logging
from typing import Any
from datetime import datetime, date, timezone
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON Formatter class for logging"""
    service_name: str

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord,
                   message_dict: dict[str, Any]):
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        log_record['service'] = self.service_name
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].lower()
        else:
            log_record['level'] = record.levelname.lower()

def json_serialize(obj):
    """Serialize datetime and date objects to isoformat strings."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)
