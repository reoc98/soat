

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def str_to_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
    """Convert a string to a datetime object."""
    try:
        return datetime.strptime(date_str, fmt)
    except ValueError:
        logger.warning(f"Invalid date format for {date_str}: {fmt}")
        return None

def change_format_date(date_str: str, current_fmt: str, target_fmt: str) -> str:
    """Change the format of a date string."""
    try:
        date_obj = str_to_date(date_str, current_fmt)
        if date_obj:
            return date_obj.strftime(target_fmt)
    except Exception as e:
        logger.error(f"Error changing date format for {date_str}: {e}")
    return None