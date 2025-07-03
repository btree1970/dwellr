from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class EmailData:
    """Structured email data for rental inquiries"""
    
    subject: str
    body: str
    to_email: str
    to_name: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    listing_id: Optional[str] = None
    generated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()