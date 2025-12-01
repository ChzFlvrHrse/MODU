from openai import AsyncOpenAI
from pypdf import PdfReader
from dotenv import load_dotenv
import os, json, logging, asyncio
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Division(BaseModel):
    division_code: str = Field(description="CSI division code (e.g., '03')")
    division_name: str = Field(description="Name of the division (e.g., 'Concrete')")
    page_range: list[int] = Field(description="Start and end page numbers", default=[])
    scope_summary: str = Field(description="Summary of the scope for this division", default="")
    assumptions_or_risks: list[str] = Field(description="List of assumptions or risks identified", default=[])
    keywords_found: list[str] = Field(description="Relevant keywords found in the spec", default=[])

class DivisionBreakdown(BaseModel):
    divisions_detected: list[Division] = Field(description="A list of detected divisions", default=[])
    notes: str = Field(description="Any uncertainty or questions", default="")

async def division_breakdown(spec_text: str) -> DivisionBreakdown:
    response = await client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert construction estimator. "
                    "Given a section of a spec sheet, your job is to detect which CSI divisions are present "
                    "and extract only what is relevant to each division. "
                    "Analyze the text and identify divisions by their CSI codes (e.g., '03' for Concrete, '09' for Finishes)."
                )
            },
            {
                "role": "user",
                "content": spec_text
            },
        ],
        response_format=DivisionBreakdown,
    )

    return response.choices[0].message.parsed

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


async def test_division_breakdown():
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "example_spec.pdf",
    )

    # 🔹 Start small: first 3–5 pages so you don't blow the context window
    spec_text = await extract_pages(pdf_path, start_page=0, end_page=8)

    logger.info(f"Extracted characters: {len(spec_text)}")
    # print(spec_text[:1000])  # uncomment if you want to sanity-check the raw text

    result = await division_breakdown(spec_text)

    # result is a Pydantic model; dump it as pretty JSON
    logger.info(json.dumps(result.model_dump(), indent=2))
    return result

result = asyncio.run(test_division_breakdown())
print(result)
