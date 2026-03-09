import fitz  # PyMuPDF
from google import genai
import os
import json
from typing import List, Dict, Union

class ITPProcessor:
    def __init__(self):
        # Configure Gemini API using the new google.genai SDK
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def process(self, itp_pdf_path: str, wir_sample_pdf_path: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        Step 1: ITP Processor
        Extracts a verified checklist from the ITP PDF based on the WIR Sample.
        Returns a dictionary with 'master_discipline', 'master_work_type', and 'checklist_items'.
        """
        # 1. Extract text from ITP
        itp_text = self._extract_text(itp_pdf_path)
        
        # 2. Extract text from WIR Sample
        wir_sample_text = self._extract_text(wir_sample_pdf_path)
        
        # 3. Use Gemini to extract and verify the checklist and work type
        extracted_data = self._extract_data_with_gemini(itp_text, wir_sample_text)
        return extracted_data

    def _extract_text(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF."""
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def _extract_data_with_gemini(self, itp_text: str, wir_sample_text: str) -> Dict[str, Union[str, List[Dict]]]:
        """
        Send extracted text to Gemini for structured data generation (checklist, discipline, work type).
        """
        prompt = f"""
        You are a Senior Construction Engineer at MBL. Your task is to extract a 'Work Inspection Request (WIR)' checklist from the following ITP (Inspection and Test Plan) document.
        Additionally, you need to identify the overall 'Discipline' and 'Work Type' for this ITP, which will serve as the master type for the session.

        The checklist must strictly follow the terminology and formatting style seen in the 'WIR Sample' text provided below.
        
        ### ITP Document Content:
        {itp_text}

        ### WIR Sample Content:
        {wir_sample_text}

        ### Instructions:
        1. Identify the primary 'Discipline' (e.g., Civil, Electrical, Mechanical, Structural, Architectural) and the specific 'Work Type' (e.g., Concrete Installation, Small Power Wiring, HVAC Ductwork, Steel Erection, Wall Partitioning) that this ITP primarily covers. These should be high-level and clear.
        2. Identify the inspection items, activity descriptions, and acceptance criteria from the ITP.
        3. Format them into a structured checklist (list of items).
        4. Each checklist item should include:
           - 'item_number': Sequential number.
           - 'activity': Concise description of the inspection activity.
           - 'acceptance_criteria': The standard or measurement used for acceptance.
           - 'reference': Any document or clause reference (if available).
        
        Output the result as a JSON object with two top-level keys:
        - 'master_discipline': (string, identified discipline)
        - 'master_work_type': (string, identified work type)
        - 'checklist_items': (JSON array of checklist item objects)

        Return ONLY the JSON object.
        """

        # Using the new google.genai SDK method
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        # Extract JSON from response (handling potential markdown)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            parsed_result = json.loads(content)
            # Validate expected top-level keys
            if not isinstance(parsed_result, dict) or \
               "master_discipline" not in parsed_result or \
               "master_work_type" not in parsed_result or \
               "checklist_items" not in parsed_result:
                raise ValueError("Gemini response is not in the expected format (missing master_discipline, master_work_type, or checklist_items).")
            return parsed_result
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from Gemini response: {content}")
            raise ValueError("Gemini returned invalid JSON for ITP extraction.")
        except ValueError as ve:
            logger.error(f"Error validating Gemini response: {ve}. Content: {content}")
            raise ve
