import pytz
from datetime import datetime
from typing import Optional

def get_pst_date(date: Optional[datetime] = None) -> datetime:
    if date:
        return date.astimezone(pytz.timezone('US/Pacific'))
    return datetime.now(pytz.timezone('US/Pacific'))