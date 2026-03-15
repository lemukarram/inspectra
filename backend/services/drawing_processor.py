import fitz # PyMuPDF
from google import genai
import os
import json
from typing import List, Dict, Union, Optional
import logging
from fastapi import HTTPException
import PIL.Image
import io

#settings for logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DrawingProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set for DrawingProcessor")
        self.client = genai.Client(api_key=api_key)
        self.model_id = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")

    async def process(self, 
                      drawing_path: str, 
                      wir_sample_path: str, 
                      checklist_items: List[Dict]) -> Dict[str, Union[str, List[str]]]:
        

        """
        Step 3: Drawing & Location Processor
        Extracts discipline, work type, location details (grid lines, levels, zones), 
        Drawing Number, Revision, Approval Status, Grid Axes (e.g., 1-5, A-D), and Floor/Level from a 2D drawing (PDF/Image)
        Also extracts followings if availabe in the drawing:
        Civil/Structural information: Read Reinforcement Tables for bar sizes and spacing.
        Architectural information: Read Room Finish Schedules for ceiling, wall, and floor materials.
        Electrical/Low Current information: Read Legends for conduit types and mounting heights.
        Mechanical information: Read Pipe/Duct Schedules for diameters and insulation types.
        Survey information: Extract Benchmarks and Reduced Levels (RL).
        Landscape/Facade/HSE information: Extract specific technical notes or material callouts relevant to the plan view
        using Gemini Vision, referencing the WIR Sample and checklist items.
        
        Args:
            drawing_path (str): Path to the 2D drawing PDF/Image.
            wir_sample_path (str): Path to the WIR Sample PDF.
            checklist_items (List[Dict]): List of verified checklist items (from Step 1 & 2).

        Returns:
            Dict: A dictionary containing extracted values in key value format.
        """
        
        # Prepare image from drawing for Gemini Vision
        pil_image = None
        file_extension = os.path.splitext(drawing_path)[1].lower()
        if file_extension == ".pdf":
            img_bytes = self._extract_image_from_pdf(drawing_path)
            if img_bytes:
                try:
                    pil_image = PIL.Image.open(io.BytesIO(img_bytes))
                except Exception as e:
                    logger.error(f"Failed to convert PDF image bytes to PIL Image for {drawing_path}: {e}")
                    raise HTTPException(status_code=400, detail=f"Failed to process drawing PDF image: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="No images could be extracted from the provided PDF drawing.")
        elif file_extension in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            try:
                pil_image = PIL.Image.open(drawing_path)
            except Exception as e:
                logger.error(f"Failed to open image file {drawing_path}: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to open drawing image: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported drawing file type: {file_extension}")

        if not pil_image:
            # Return a structure consistent with expected output, with N/A for discipline/work_type
            return {"extracted_discipline": "N/A", "extracted_work_type": "N/A", "grid_lines": [], "levels": [], "zone": None}

        # 2. Extract text from WIR Sample (for context)
        wir_sample_text = self._extract_text_from_pdf(wir_sample_path)
        # 3. Construct the prompt for Gemini Vision
        # Provide both image and text context
        prompt_parts_text = [
            "You are a Senior Construction Engineer at MBL. Analyze the provided 2D construction drawing.",
            "Identify the overall 'Discipline' (e.g., Civil, Electrical, Mechanical, Structural, Architectural) and the specific 'Work Type' (e.g., Concrete Installation, Small Power Wiring, HVAC Ductwork, Steel Erection, Wall Partitioning) that this drawing primarily covers, typically found in the title block or general notes. These should be high-level and clear.",
            "Additionally, identify the master location details for the overall drawing based on typical construction drawing conventions.",
            "Specifically, extract the 'Grid Lines' (e.g., A-D, 1-3, etc.), 'Levels/Elevations' (e.g., Level 1, +100.00), and the general 'Room/Area Name' or 'Zone' the drawing pertains to.",
            "additionally identify Drawing Number, Revision, Approval Status, Grid Axes (e.g., 1-5, A-D), and Floor/Level from a 2D drawing (PDF/Image)"
            "Also extracts followings if availabe in the drawing:"
            "Civil/Structural information: Read Reinforcement Tables for bar sizes and spacing."
            "Architectural information: Read Room Finish Schedules for ceiling, wall, and floor materials."
            "Electrical/Low Current information: Read Legends for conduit types and mounting heights."
            "Mechanical information: Read Pipe/Duct Schedules for diameters and insulation types."
            "Survey information: Extract Benchmarks and Reduced Levels (RL)."
            "Landscape/Facade/HSE information: Extract specific technical notes or material callouts relevant to the plan view"
            "Consider the following WIR Sample text for context regarding terminology and expected outputs:",
            wir_sample_text,
            "Also, here are the current checklist items which may provide additional context, though focus on master drawing locations:",
            json.dumps(checklist_items),
            "Output the results as a JSON object A dictionary containing extracted values in key value format. Return ONLY the JSON object.",
        ]

        contents_for_gemini = prompt_parts_text + [pil_image] # Add PIL image directly

        try:
            #response = await self.client.models.generate_content_async(
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=contents_for_gemini
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

    def _extract_image_from_pdf(self, pdf_path: str, page_number: int = 0) -> Optional[bytes]:
        """
        Extracts the first page of a PDF as PNG bytes.
        """
        try:
            doc = fitz.open(pdf_path)
            if page_number >= len(doc):
                return None
            
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            
            # Convert to bytes
            img_bytes = pix.tobytes("png")
            return img_bytes
        except Exception as e:
            logger.error(f"Failed to extract image from PDF {pdf_path}: {e}")
            return None

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