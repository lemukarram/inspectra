import fitz  # PyMuPDF
from google import genai
import os
import json
from typing import List, Dict, Union
import logging

logger = logging.getLogger(__name__)

class MESProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def process(self, mes_pdf_path: str, wir_sample_pdf_path: str, checklist_items: List[Dict]) -> Dict[str, Union[str, List[Dict]]]:
        """
        Step 2: MES Processor
        Enriches the checklist with procedure and safety details from the MES.
        Returns a dictionary with 'extracted_discipline', 'extracted_work_type', and 'enriched_checklist_items'.
        """
        # 1. Extract text from MES
        mes_text = self._extract_text(mes_pdf_path)

        # 2. Extract text from WIR Sample
        wir_sample_text = self._extract_text(wir_sample_pdf_path)

        # 3. Use Gemini to enrich the checklist and extract discipline/work type
        enriched_data = self._enrich_data_with_gemini(mes_text, wir_sample_text, checklist_items)
        return enriched_data

    def _extract_text(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF."""
        text = ""
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"PDF path not found: {pdf_path}")
            return text
            
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text()
        except Exception as e:
            print(f"Failed to read PDF {pdf_path}: {e}")
        return text

    def _enrich_data_with_gemini(self, mes_text: str, wir_sample_text: str, checklist_items: List[Dict]) -> Dict[str, Union[str, List[Dict]]]:
        checklist_json = json.dumps(checklist_items, indent=2)
        prompt = f"""
        You are a Senior Construction Engineer at MBL. Your task is to enrich an existing 'Work Inspection Request (WIR)' checklist by finding the relevant working procedures and safety requirements for each item from the provided Method Statement (MES) document.
        Additionally, you need to identify the overall 'Discipline' and 'Work Type' for this Method Statement, which will be used for cross-validation.

        The formatting should align with the context seen in the 'WIR Sample' below.

        ### MES Document Content:
        {mes_text}

        ### WIR Sample Content:
        {wir_sample_text}

        ### Existing Checklist Items:
        {checklist_json}

        ### Instructions:
        1. Identify the primary 'Discipline' (e.g., Civil, Electrical, Mechanical, Structural, Architectural) and the specific 'Work Type' (e.g., Concrete Installation, Small Power Wiring, HVAC Ductwork, Steel Erection, Wall Partitioning) that this MES primarily covers. These should be high-level and clear.
        2. Read through the existing checklist items.
        3. For each item, search the 'MES Document Content' for the corresponding 'Working Procedure' or 'Execution' methodology, and any specific 'Safety Requirements'.
        4. Keep the explanations concise, relevant, and focused on linking the 'How-to' from the MES to the 'What-to-check' from the ITP.
        5. If no relevant procedure or safety information is found for an item, use "N/A".
        
        Output the result as a JSON object with two top-level keys:
        - 'extracted_discipline': (string, identified discipline from MES)
        - 'extracted_work_type': (string, identified work type from MES)
        - 'enriched_checklist_items': (JSON array of enriched checklist item objects, where each object includes "id", "procedure_text", and "safety_text")

        Return ONLY the JSON object.
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            parsed_result = json.loads(content)
            # Validate expected top-level keys
            if not isinstance(parsed_result, dict) or \
               "extracted_discipline" not in parsed_result or \
               "extracted_work_type" not in parsed_result or \
               "enriched_checklist_items" not in parsed_result:
                raise ValueError("Gemini response is not in the expected format (missing extracted_discipline, extracted_work_type, or enriched_checklist_items).")
            return parsed_result
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from Gemini response: {content}")
            raise ValueError("Gemini returned invalid JSON for MES enrichment.")
        except ValueError as ve:
            logger.error(f"Error validating Gemini response: {ve}. Content: {content}")
            raise ve
