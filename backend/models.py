from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class WIRSession(Base):
    __tablename__ = "wir_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    status = Column(String, default="INITIALIZED") # INITIALIZED, ITP_EXTRACTED, HUMAN_VERIFIED, FINALIZED
    state = Column(JSON, default={}) # To store state machine data as JSONB
    
    itp_filename = Column(String, nullable=True)
    wir_sample_filename = Column(String, nullable=True)
    
    # Store extracted data for Step 1
    extracted_checklist = Column(JSON, default=[])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
