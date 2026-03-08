from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import uuid
import models
from database import engine, get_db, Base
from services.itp_processor import ITPProcessor
from services.mes_processor import MESProcessor
import os
import time
from sqlalchemy.exc import OperationalError
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware

# Global service instance to prevent multiple objects
itp_processor = None
mes_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    global itp_processor, mes_processor
    itp_processor = ITPProcessor()
    mes_processor = MESProcessor()
    
    # Optional: Initial DB check/creation (though migrations are preferred)
    retries = 5
    while retries > 0:
        try:
            # This creates tables if they don't exist. 
            # Note: It won't add columns to existing tables (Alembic is better for that).
            models.Base.metadata.create_all(bind=engine)
            print("Successfully connected to the database.")
            break
        except OperationalError:
            retries -= 1
            print(f"Database connection failed. Retrying... ({5-retries}/5)")
            time.sleep(2)
    
    yield
    # Shutdown: Clean up if needed
    pass

app = FastAPI(title="WIR Inspector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChecklistItemBase(BaseModel):
    item_number: Optional[str] = None
    item_text: str
    acceptance_criteria: str
    control_point: Optional[str] = None
    procedure_text: Optional[str] = None
    safety_text: Optional[str] = None

class ChecklistItemSchema(ChecklistItemBase):
    id: int
    session_id: str
    class Config:
        from_attributes = True

class WIRSessionSchema(BaseModel):
    id: int
    session_id: str
    session_name: Optional[str] = None
    status: str
    current_step: int
    created_at: str
    class Config:
        from_attributes = True

@app.post("/session/initialize")
async def initialize_session(
    itp_file: UploadFile = File(...),
    wir_sample: UploadFile = File(...),
    session_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    session_id = str(uuid.uuid4())
    os.makedirs("uploads", exist_ok=True)
    
    itp_path = f"uploads/{session_id}_itp.pdf"
    wir_path = f"uploads/{session_id}_wir.pdf"
    
    with open(itp_path, "wb") as f:
        f.write(await itp_file.read())
    with open(wir_path, "wb") as f:
        f.write(await wir_sample.read())
    
    session = models.WIRSession(
        session_id=session_id,
        session_name=session_name,
        status="INITIALIZED",
        current_step=1,
        itp_filename=itp_path,
        wir_sample_filename=wir_path
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Use global itp_processor
    extracted_checklist = await itp_processor.process(itp_path, wir_path)
    
    for item in extracted_checklist:
        db_item = models.ChecklistItem(
            session_id=session_id,
            item_number=item.get("item_number"),
            item_text=item.get("activity") or item.get("item_text") or "N/A",
            acceptance_criteria=item.get("acceptance_criteria") or "N/A",
            control_point=item.get("reference") or item.get("control_point") or "N/A"
        )
        db.add(db_item)
    
    session.status = "ITP_EXTRACTED"
    db.commit()
    db.refresh(session)
    
    return {
        "session_id": session_id, 
        "session_name": session_name, 
        "checklist": [ChecklistItemSchema.from_orm(it) for it in session.checklist_items]
    }

@app.post("/wir/session/{session_id}/step2")
async def process_step2(
    session_id: str,
    mes_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    session = db.query(models.WIRSession).filter(models.WIRSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    os.makedirs("uploads", exist_ok=True)
    mes_path = f"uploads/{session_id}_mes.pdf"
    
    with open(mes_path, "wb") as f:
        f.write(await mes_file.read())
        
    session.mes_filename = mes_path
    db.commit()

    # Get checklist items from DB
    items = db.query(models.ChecklistItem).filter(models.ChecklistItem.session_id == session_id).all()
    checklist_dicts = [{"id": item.id, "item_number": item.item_number, "item_text": item.item_text, "acceptance_criteria": item.acceptance_criteria} for item in items]
    
    # Process with AI
    enriched_data = await mes_processor.process(mes_path, session.wir_sample_filename, checklist_dicts)
    
    # Update DB with enriched data
    for ed in enriched_data:
        item_id = ed.get("id")
        if item_id:
            db_item = db.query(models.ChecklistItem).filter(models.ChecklistItem.id == item_id).first()
            if db_item:
                db_item.procedure_text = ed.get("procedure_text", "N/A")
                db_item.safety_text = ed.get("safety_text", "N/A")
                
    session.current_step = 2
    session.status = "MES_EXTRACTED"
    db.commit()
    
    updated_items = db.query(models.ChecklistItem).filter(models.ChecklistItem.session_id == session_id).order_by(models.ChecklistItem.id.asc()).all()
    return {"status": "success", "checklist": [ChecklistItemSchema.from_orm(it) for it in updated_items]}

@app.put("/wir/session/{session_id}/step/{step_number}")
def set_session_step(session_id: str, step_number: int, db: Session = Depends(get_db)):
    session = db.query(models.WIRSession).filter(models.WIRSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.current_step = step_number
    db.commit()
    return {"status": "success", "current_step": session.current_step}

@app.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(models.WIRSession).order_by(models.WIRSession.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "session_id": s.session_id,
            "session_name": s.session_name,
            "status": s.status,
            "current_step": s.current_step,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in sessions
    ]

@app.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(models.WIRSession).filter(models.WIRSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "session_id": session.session_id,
        "session_name": session.session_name,
        "status": session.status,
        "current_step": session.current_step,
        "itp_filename": session.itp_filename,
        "wir_sample_filename": session.wir_sample_filename,
        "mes_filename": session.mes_filename,
        "created_at": session.created_at.isoformat() if session.created_at else None
    }

@app.get("/sessions/{session_id}/checklist")
def get_checklist(session_id: str, db: Session = Depends(get_db)):
    items = db.query(models.ChecklistItem).filter(models.ChecklistItem.session_id == session_id).order_by(models.ChecklistItem.id.asc()).all()
    return items

@app.put("/checklist/{item_id}")
def update_checklist_item(item_id: int, item_update: ChecklistItemBase, db: Session = Depends(get_db)):
    item = db.query(models.ChecklistItem).filter(models.ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.item_number = item_update.item_number
    item.item_text = item_update.item_text
    item.acceptance_criteria = item_update.acceptance_criteria
    item.control_point = item_update.control_point
    item.procedure_text = item_update.procedure_text
    item.safety_text = item_update.safety_text
    
    db.commit()
    return {"status": "success"}

@app.delete("/checklist/{item_id}")
def delete_checklist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ChecklistItem).filter(models.ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return {"status": "success"}

@app.put("/wir/session/{session_id}/verify")
def verify_checklist(session_id: str, db: Session = Depends(get_db)):
    session = db.query(models.WIRSession).filter(models.WIRSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # We could set status depending on current_step
    if session.current_step == 1:
        session.status = "STEP_1_VERIFIED"
    elif session.current_step == 2:
        session.status = "STEP_2_VERIFIED"
        
    db.commit()
    return {"status": "success"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
