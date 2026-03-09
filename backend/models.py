from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB # Import JSONB
from database import Base

class WIRSession(Base):
    __tablename__ = "wir_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    session_name = Column(String, nullable=True) # User-defined name for the session
    master_discipline = Column(String, nullable=True) # New field for work type lock
    master_work_type = Column(String, nullable=True)  # New field for work type lock
    status = Column(String, default="INITIALIZED") # INITIALIZED, ITP_EXTRACTED, HUMAN_VERIFIED, FINALIZED
    current_step = Column(Integer, default=1)
    state = Column(JSON, default={}) # To store state machine data as JSONB
    
    itp_filename = Column(String, nullable=True)
    wir_sample_filename = Column(String, nullable=True)
    mes_filename = Column(String, nullable=True)
    drawing_filename = Column(String, nullable=True) # New field


    # New fields for Drawing & Location Processor
    grid_lines = Column(JSONB, nullable=True)
    levels = Column(JSONB, nullable=True)
    zone = Column(String, nullable=True)
    
    # Relationship to checklist items
    checklist_items = relationship("ChecklistItem", back_populates="session", cascade="all, delete-orphan")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("wir_sessions.session_id"))
    item_number = Column(String, nullable=True)
    item_text = Column(String) # Previously 'activity'
    acceptance_criteria = Column(String)
    control_point = Column(String, nullable=True) # Previously 'reference'
    procedure_text = Column(String, nullable=True)
    safety_text = Column(String, nullable=True)
    
    session = relationship("WIRSession", back_populates="checklist_items")

