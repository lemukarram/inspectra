from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import models
from database import engine, get_db, Base
from services.itp_processor import ITPProcessor
import os
import time
from sqlalchemy.exc import OperationalError

from fastapi.middleware.cors import CORSMiddleware

# Simple retry logic for database connection at startup
def init_db():
    retries = 5
    while retries > 0:
        try:
            models.Base.metadata.create_all(bind=engine)
            print("Successfully connected to the database.")
            break
        except OperationalError as e:
            retries -= 1
            print(f"Database connection failed. Retrying... ({5-retries}/5)")
            time.sleep(2)
    if retries == 0:
        print("Could not connect to the database after several retries.")

init_db()

app = FastAPI(title="WIR Inspector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/session/initialize")
async def initialize_session(
    itp_file: UploadFile = File(...),
    wir_sample: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    session_id = str(uuid.uuid4())
    
    # Save files (in a real app, use a more robust storage)
    itp_path = f"uploads/{session_id}_itp.pdf"
    wir_path = f"uploads/{session_id}_wir.pdf"
    os.makedirs("uploads", exist_ok=True)
    
    with open(itp_path, "wb") as f:
        f.write(await itp_file.read())
        
    with open(wir_path, "wb") as f:
        f.write(await wir_sample.read())
    
    session = models.WIRSession(
        session_id=session_id,
        status="INITIALIZED",
        itp_filename=itp_path,
        wir_sample_filename=wir_path
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Run Step 1: ITP Processor
    itp_processor = ITPProcessor()
    extracted_checklist = await itp_processor.process(itp_path, wir_path)
    session.extracted_checklist = extracted_checklist
    session.status = "ITP_EXTRACTED"
    db.commit()
    
    return {"session_id": session_id, "checklist": extracted_checklist}

@app.get("/session/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(models.WIRSession).filter(models.WIRSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.get("/health")
def health_check():
    return {"status": "ok"}
