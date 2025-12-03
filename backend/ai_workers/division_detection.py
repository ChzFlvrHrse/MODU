from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
import os, json, logging, sys, base64, asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))
from helper_functions.rasterization import rasterize_pdf

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class DivisionSource(BaseModel):
    page_range: str = Field(description="Start and end page numbers in the format 'page X to page Y'", default="")
    character_count: str = Field(description="Number of characters in the page range in the format 'X'", default="")

class DivisionSectionNumbers(BaseModel):
    section_number: str = Field(description="Section numbers for this division (e.g, '000003', '013100a')", default="")
    title: str = Field(description="Section names for the section number (e.g, 'GENERAL CONDITIONS AIA A201')", default="")

class Division(BaseModel):
    sources: DivisionSource = Field(description="A source for this division", default=None)
    division_code: str = Field(description="CSI division code (e.g., '03')")
    division_title: str = Field(description="Name of the division (e.g., 'Concrete')")
    page_range: list[int] = Field(description="start page and end page numbers", default=[])
    section: list[DivisionSectionNumbers] = Field(description="Section numbers for this division", default=[])
    scope_summary: str = Field(description="Summary of the scope for this division", default="")
    assumptions_or_risks: list[str] = Field(description="List of assumptions or risks identified", default=[])
    keywords_found: list[str] = Field(description="Relevant keywords found in the spec", default=[])

class DivisionBreakdown(BaseModel):
    divisions_detected: list[Division] = Field(description="A list of detected divisions", default=[])
    notes: str = Field(description="Any uncertainty or questions", default="")

async def division_detection_ai(spec_pages: list[dict[int, bytes]]) -> dict:
    response = await client.beta.chat.completions.parse(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert construction estimator."
                    "Given a section of a spec sheet, your job is to detect which CSI divisions are present."
                    "Divisions are always in CSI Master Format."
                    "Analyze the text and identify divisions by their CSI codes (e.g., '03' for Concrete, '09' for Finishes)."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze the following pages of a spec sheet and detect which CSI divisions are present."},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(page['bytes']).decode('utf-8')}"}} for page in spec_pages]
                ]
            }
        ],
        response_format=DivisionBreakdown
    )

    # Convert DivisionBreakdown to JSON dict
    res = json.loads(json.dumps({**response.choices[0].message.parsed.model_dump()}))

    # return {"source": {"page_range": f"page {start_page} to page {end_page}"}, **res}
    return res

async def divisions(
    pdf_path: str,
    batch_size: int = 10,
    dpi: int = 200,
    start_index: int = 0,
    end_index: int = 10
) -> list[dict]:
    detected_divisions: list[dict] = []
    batch: list[dict[int, bytes]] = []

    if batch_size > 20:
        raise ValueError("Batch size must be less than or equal to 20")

    async for page in rasterize_pdf(pdf_path, dpi=dpi, start_index=start_index, end_index=end_index):
        batch.append(page)
        if len(batch) >= batch_size:
            div = await division_detection_ai(batch)
            div_dict = div["divisions_detected"]
            detected_divisions.extend(div_dict)

            logger.info("Divisions: ", {"".join([f"{item['division_code']} - {item['division_title']}" for item in div_dict])})
            logger.info(f"Divisions detected: {len(detected_divisions)}")

            batch = []

    if batch:
        div = await division_detection_ai(batch)
        div_dict = div["divisions_detected"]
        detected_divisions.extend(div_dict)

        logger.info("Divisions: ", {"".join([f"{item['division_code']} - {item['division_title']}" for item in div_dict])})
        logger.info(f"Total detected divisions: {len(detected_divisions)}")

    return detected_divisions


result = asyncio.run(divisions(pdf_path="example_spec.pdf", batch_size=5, dpi=200, start_index=0, end_index=10))
print(result)
