import fitz # PyMuPDF
from google import genai
import os
import json
from typing import List, Dict, Union
import logging
from fastapi import HTTPException # New Import

logger = logging.getLogger(__name__)

class DrawingProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set for DrawingProcessor")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_VISION_MODEL", "gemini-pro-vision") # Using a vision model

    async def process(self, 
                      drawing_path: str, 
                      wir_sample_path: str, 
                      checklist_items: List[Dict]) -> Dict[str, Union[str, List[str]]]:
        """
        Step 3: Drawing & Location Processor
        Extracts discipline, work type, and location details (grid lines, levels, zones) from a 2D drawing (PDF/Image)
        using Gemini Vision, referencing the WIR Sample and checklist items.
        
        Args:
            drawing_path (str): Path to the 2D drawing PDF/Image.
            wir_sample_path (str): Path to the WIR Sample PDF.
            checklist_items (List[Dict]): List of verified checklist items (from Step 1 & 2).

        Returns:
            Dict: A dictionary containing extracted 'extracted_discipline', 'extracted_work_type', 'grid_lines', 'levels', and 'zone'.
        """
        
        # 1. Prepare images from drawing for Gemini Vision
        # If PDF, convert to image. For simplicity, we'll assume the first page for now.
        image_parts = self._extract_image_from_pdf(drawing_path)

        if not image_parts:
            logger.warning(f"No images extracted from drawing: {drawing_path}")
            # Return a structure consistent with expected output, with N/A for discipline/work_type
            return {"extracted_discipline": "N/A", "extracted_work_type": "N/A", "grid_lines": [], "levels": [], "zone": None}

        # 2. Extract text from WIR Sample (for context)
        wir_sample_text = self._extract_text_from_pdf(wir_sample_path)
        
        # 3. Construct the prompt for Gemini Vision
        # Provide both image and text context
        prompt_parts = [
            "You are a Senior Construction Engineer at MBL. Analyze the provided 2D construction drawing.",
            "Identify the overall 'Discipline' (e.g., Civil, Electrical, Mechanical, Structural, Architectural) and the specific 'Work Type' (e.g., Concrete Installation, Small Power Wiring, HVAC Ductwork, Steel Erection, Wall Partitioning) that this drawing primarily covers, typically found in the title block or general notes. These should be high-level and clear.",
            "Additionally, identify the master location details for the overall drawing based on typical construction drawing conventions.",
            "Specifically, extract the 'Grid Lines' (e.g., A-D, 1-3, etc.), 'Levels/Elevations' (e.g., Level 1, +100.00), and the general 'Room/Area Name' or 'Zone' the drawing pertains to.",
            "Consider the following WIR Sample text for context regarding terminology and expected outputs:",
            wir_sample_text,
            "Also, here are the current checklist items which may provide additional context, though focus on master drawing locations:",
            json.dumps(checklist_items),
            "Output the results as a JSON object with the following keys: 'extracted_discipline' (string), 'extracted_work_type' (string), 'grid_lines' (list of strings), 'levels' (list of strings), and 'zone' (string). Return ONLY the JSON object.",
            *image_parts # Add image data for multimodal input
        ]

        try:
            response = await self.client.models.generate_content_async(
                model=self.model,
                contents=prompt_parts
            )
            
            content = response.text.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()

            result = json.loads(content)
            
            # Basic validation of the result structure
            if not isinstance(result, dict):
                raise ValueError("Gemini response is not a dictionary.")
            if "extracted_discipline" not in result or not isinstance(result["extracted_discipline"], str):
                result["extracted_discipline"] = "N/A"
            if "extracted_work_type" not in result or not isinstance(result["extracted_work_type"], str):
                result["extracted_work_type"] = "N/A"
            if "grid_lines" not in result or not isinstance(result["grid_lines"], list):
                result["grid_lines"] = []
            if "levels" not in result or not isinstance(result["levels"], list):
                result["levels"] = []
            if "zone" not in result or not isinstance(result["zone"], (str, type(None))):
                result["zone"] = None

            return result

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from Gemini response: {content}")
            raise ValueError("Gemini returned invalid JSON for Drawing processing.")
        except ValueError as ve:
            logger.error(f"Error validating Gemini response: {ve}. Content: {content}")
            raise ve
        except Exception as e:
            logger.error(f"Error during Gemini Vision analysis for drawing {drawing_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Drawing & Location analysis failed: {str(e)}")

    def _extract_image_from_pdf(self, pdf_path: str, page_number: int = 0) -> List[Dict]:
        """
        Extracts the first page of a PDF as an image for Gemini Vision.
        Returns a list of dictionaries in the format expected by genai.upload_file.
        """
        try:
            doc = fitz.open(pdf_path)
            if page_number >= len(doc):
                logger.warning(f"Page {page_number} not found in PDF {pdf_path}.")
                return []
            
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            
            # Convert to bytes
            img_bytes = pix.tobytes("png")

            return [
                {
                    "mime_type": "image/png",
                    "data": img_bytes
                }
            ]
        except Exception as e:
            logger.error(f"Failed to extract image from PDF {pdf_path}: {e}")
            return []

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF."""
        text = ""
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
        return text