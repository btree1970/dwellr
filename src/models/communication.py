from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from src.database.db import Base


class CommunicationType(Enum):
    """Types of communication"""
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    WHATSAPP = "whatsapp"


class CommunicationStatus(Enum):
    """Status of communication"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    REPLIED = "replied"


class Communication(Base):
    """Model for tracking rental listing communications"""
    __tablename__ = "communications"
    
    # SQLAlchemy column definitions
    id = Column(String, primary_key=True)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False)
    communication_type = Column(SQLEnum(CommunicationType), nullable=False)
    status = Column(SQLEnum(CommunicationStatus), nullable=False)
    subject = Column(String, nullable=True)
    body = Column(String, nullable=True)
    to_email = Column(String, nullable=True)
    to_phone = Column(String, nullable=True)
    to_name = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    from_phone = Column(String, nullable=True)
    from_name = Column(String, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    response_received_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Relationship
    listing = relationship("Listing", back_populates="communications")
    
    def __init__(self, **kwargs):
        """Initialize with default values"""
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        if 'generated_at' not in kwargs:
            kwargs['generated_at'] = datetime.now()
        super().__init__(**kwargs)
    
    @classmethod
    def create_email(cls, listing_id: str, subject: str, body: str, 
                    to_email: str, to_name: Optional[str] = None,
                    from_email: Optional[str] = None, from_name: Optional[str] = None) -> 'Communication':
        """Create a new email communication"""
        return cls(
            id=str(uuid.uuid4()),
            listing_id=listing_id,
            communication_type=CommunicationType.EMAIL,
            status=CommunicationStatus.PENDING,
            subject=subject,
            body=body,
            to_email=to_email,
            to_name=to_name,
            from_email=from_email,
            from_name=from_name
        )
    
    @classmethod
    def create_sms(cls, listing_id: str, body: str, 
                  to_phone: str, to_name: Optional[str] = None,
                  from_phone: Optional[str] = None, from_name: Optional[str] = None) -> 'Communication':
        """Create a new SMS communication"""
        return cls(
            id=str(uuid.uuid4()),
            listing_id=listing_id,
            communication_type=CommunicationType.SMS,
            status=CommunicationStatus.PENDING,
            body=body,
            to_phone=to_phone,
            to_name=to_name,
            from_phone=from_phone,
            from_name=from_name
        )
    
    def mark_sent(self, sent_at: Optional[datetime] = None):
        """Mark communication as sent"""
        self.status = CommunicationStatus.SENT
        self.sent_at = sent_at or datetime.now()
        self.attempts += 1
        self.last_attempt_at = self.sent_at
    
    def mark_failed(self, error_message: str, failed_at: Optional[datetime] = None):
        """Mark communication as failed"""
        self.status = CommunicationStatus.FAILED
        self.error_message = error_message
        self.attempts += 1
        self.last_attempt_at = failed_at or datetime.now()
    
    def mark_delivered(self, delivered_at: Optional[datetime] = None):
        """Mark communication as delivered"""
        self.status = CommunicationStatus.DELIVERED
        self.delivered_at = delivered_at or datetime.now()
    
    def mark_replied(self, replied_at: Optional[datetime] = None):
        """Mark communication as replied to"""
        self.status = CommunicationStatus.REPLIED
        self.response_received_at = replied_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'communication_type': self.communication_type.value,
            'status': self.status.value,
            'subject': self.subject,
            'body': self.body,
            'to_email': self.to_email,
            'to_phone': self.to_phone,
            'to_name': self.to_name,
            'from_email': self.from_email,
            'from_phone': self.from_phone,
            'from_name': self.from_name,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'response_received_at': self.response_received_at.isoformat() if self.response_received_at else None,
            'attempts': self.attempts,
            'last_attempt_at': self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Communication':
        """Create Communication from dictionary (database row)"""
        from dateutil import parser
        
        return cls(
            id=data['id'],
            listing_id=data['listing_id'],
            communication_type=CommunicationType(data['communication_type']),
            status=CommunicationStatus(data['status']),
            subject=data.get('subject'),
            body=data.get('body'),
            to_email=data.get('to_email'),
            to_phone=data.get('to_phone'),
            to_name=data.get('to_name'),
            from_email=data.get('from_email'),
            from_phone=data.get('from_phone'),
            from_name=data.get('from_name'),
            generated_at=parser.parse(data['generated_at']) if data.get('generated_at') else None,
            sent_at=parser.parse(data['sent_at']) if data.get('sent_at') else None,
            delivered_at=parser.parse(data['delivered_at']) if data.get('delivered_at') else None,
            response_received_at=parser.parse(data['response_received_at']) if data.get('response_received_at') else None,
            attempts=data.get('attempts', 0),
            last_attempt_at=parser.parse(data['last_attempt_at']) if data.get('last_attempt_at') else None,
            error_message=data.get('error_message')
        )
    
    def is_email(self) -> bool:
        """Check if this is an email communication"""
        return self.communication_type == CommunicationType.EMAIL
    
    def is_sms(self) -> bool:
        """Check if this is an SMS communication"""
        return self.communication_type == CommunicationType.SMS
    
    def is_pending(self) -> bool:
        """Check if communication is pending"""
        return self.status == CommunicationStatus.PENDING
    
    def is_sent(self) -> bool:
        """Check if communication was sent"""
        return self.status in [CommunicationStatus.SENT, CommunicationStatus.DELIVERED, CommunicationStatus.REPLIED]
    
    def has_failed(self) -> bool:
        """Check if communication failed"""
        return self.status == CommunicationStatus.FAILED
