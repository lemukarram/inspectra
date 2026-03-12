from typing import Optional
from models import WIRSession # Assuming models can be imported relative to backend dir
from fastapi import HTTPException
import logging
#settings for logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_document_alignment(
    session: WIRSession,
    document_type: str, # e.g., "Method Statement", "Drawing"
    extracted_discipline: Optional[str],
    extracted_work_type: Optional[str]
):
    
    return True
    logging.warning(session.master_discipline)
    logging.warning(session.master_work_type)
    if not session.master_discipline or not session.master_work_type:
        # This case should ideally not happen if Step 1 is enforced,
        # but provides a safeguard.
        raise HTTPException(
            status_code=400,
            detail=f"Validation Error: Master Work Type not established in session. "
                   f"Please complete Step 1 first."
        )

    if not extracted_discipline or not extracted_work_type:
        # If the document processor couldn't extract type, it's an issue
        raise HTTPException(
            status_code=422,
            detail=f"Validation Error: Could not extract Discipline or Work Type from {document_type}."
        )

    if (session.master_discipline.lower().strip() != extracted_discipline.lower().strip() or
        session.master_work_type.lower().strip() != extracted_work_type.lower().strip()):
        raise HTTPException(
            status_code=400,
            detail=f"Document Mismatch Error: You uploaded a {extracted_discipline}, {extracted_work_type}, {document_type} "
                   f"which does not match the session's Master Work Type of "
                   f"{session.master_discipline}, {session.master_work_type}. "
                   f"Progress blocked."
        )
    return True
