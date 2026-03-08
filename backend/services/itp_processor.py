import fitz  # PyMuPDF
from google import genai
import os
import json
from typing import List, Dict

class ITPProcessor:
    def __init__(self):
        # Configure Gemini API using the new google.genai SDK
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self.client = genai.Client(api_key=api_key)

    async def process(self, itp_pdf_path: str, wir_sample_pdf_path: str) -> List[Dict]:
        """
        Step 1: ITP Processor
        Extracts a verified checklist from the ITP PDF based on the WIR Sample.
        """
        # 1. Extract text from ITP
        itp_text = self._extract_text(itp_pdf_path)
        
        # 2. Extract text from WIR Sample
        wir_sample_text = self._extract_text(wir_sample_pdf_path)
        
        # 3. Use Gemini to extract and verify the checklist
        extracted_checklist = self._extract_checklist_with_gemini(itp_text, wir_sample_text)
        return extracted_checklist
        return extracted_checklist

    def _extract_text(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF."""
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def _extract_checklist_with_gemini(self, itp_text: str, wir_sample_text: str) -> List[Dict]:
        """
        Send extracted text to Gemini for structured checklist generation.
        """
        prompt = f"""
        You are a Senior Construction Engineer at MBL. Your task is to extract a 'Work Inspection Request (WIR)' checklist from the following ITP (Inspection and Test Plan) document.

        The checklist must strictly follow the terminology and formatting style seen in the 'WIR Sample' text provided below.
        
        ### ITP Document Content:
        {itp_text}

        ### WIR Sample Content:
        {wir_sample_text}

        ### Instructions:
        1. Identify the inspection items, activity descriptions, and acceptance criteria from the ITP.
        2. Format them into a structured checklist (list of items).
        3. Each item should include:
           - 'item_number': Sequential number.
           - 'activity': Concise description of the inspection activity.
           - 'acceptance_criteria': The standard or measurement used for acceptance.
           - 'reference': Any document or clause reference (if available).
        
        Output the result as a JSON array of objects. Return ONLY the JSON array.
        """

        # Using the new google.genai SDK method
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # Extract JSON from response (handling potential markdown)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from Gemini response: {content}")
            return []
