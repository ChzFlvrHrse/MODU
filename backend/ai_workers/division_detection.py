import os, json, logging, asyncio
from openai import AsyncOpenAI
from pypdf import PdfReader
from dotenv import load_dotenv
from pydantic import BaseModel, Field

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

async def division_detection(spec_text: str, start_page: int, end_page: int, character_count: int) -> DivisionBreakdown:
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
                "content": spec_text
            }
        ],
        response_format=DivisionBreakdown
    )

    # Convert DivisionBreakdown to JSON dict
    res = json.loads(json.dumps({**response.choices[0].message.parsed.model_dump()}))

    return {"source": {"page_range": f"page {start_page} to page {end_page}", "character_count": character_count}, **res}

async def extract_pages(path: str, start_page: int, end_page: int) -> str:
    """
    Extract text from [start_page, end_page] inclusive (0-based indexes).
    """
    reader = PdfReader(path)
    num_pages = len(reader.pages)

    start_page = max(0, start_page)
    end_page = min(end_page, num_pages - 1)

    chunks = []
    for i in range(start_page, end_page + 1):
        page = reader.pages[i]
        text = page.extract_text() or ""
        chunks.append(f"\n\n--- PAGE {i+1} ---\n{text}")

    return "\n".join(chunks)


async def all_divisions(start_page: int, end_page: int):
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "example_spec.pdf",
    )

    # 🔹 Start small: first 3–5 pages so you don't blow the context window
    spec_text = await extract_pages(pdf_path, start_page=start_page, end_page=end_page)

    logger.info(f"Pages: {start_page} to {end_page}, Extracted characters: {len(spec_text)}")
    # print(spec_text[:1000])  # uncomment if you want to sanity-check the raw text

    result = await division_detection(spec_text, start_page=start_page, end_page=end_page, character_count=len(spec_text))

    # result is a Pydantic model; dump it as pretty JSON
    return result

# result = asyncio.run(division_detection_wrapper(start_page=0, end_page=15))
# print(result)
