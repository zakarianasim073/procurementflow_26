'''Award model - Extended to support frontend expectations'''

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean

from app.db.base import Base
class Award(Base):
    """Award record - Extended to match frontend expectations"""
    __tablename__ = "awards"

    # Core identification fields
    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    
    # Frontend-expected fields
    tender_id = Column(String, nullable=True)                    # Frontend expects tender_id
    award_date = Column(DateTime, nullable=True)                  # Frontend expects award_date
    award_notice_no = Column(String, nullable=True)              # Frontend expects award_notice_no
    awarding_agency = Column(String, nullable=True)              # Frontend expects awarding_agency
    
    # Backend fields (legacy/equivalent)
    procuring_entity = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    ministry = Column(String, nullable=True)
    work_name = Column(String, nullable=False)                   # Frontend expects: tender_title
    work_type = Column(String, nullable=True)                    # Frontend expects: work_type
    district = Column(String, nullable=True)                     # Frontend expects: district
    division = Column(String, nullable=True)                     # Frontend expects: division
    
    # Award data
    estimated_cost = Column(Float, nullable=True)
    awarded_amount = Column(Float, nullable=True)
    currency = Column(String, default="BDT")
    contractor_name = Column(String, nullable=False)
    contractor_license = Column(String, nullable=True)
    contractor_address = Column(String, nullable=True)
    contract_period_days = Column(Integer, nullable=True)
    work_start_date = Column(DateTime, nullable=True)
    work_completion_date = Column(DateTime, nullable=True)
    
    # Legacy system data
    raw_data = Column(Text, nullable=True)
    boq_items = Column(Text, nullable=True)
    discount_pct = Column(Float, nullable=True)
    unit_rates = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Award(id={self.id}, title={self.work_name}, agency={self.awarding_agency or self.procuring_entity})>"
