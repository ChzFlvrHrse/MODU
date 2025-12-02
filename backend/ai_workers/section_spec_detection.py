from pathlib import Path
from pypdf import PdfReader
from dotenv import load_dotenv
from openai import AsyncOpenAI
from typing import Optional, Tuple
import os, logging, re, asyncio, sys
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))
from helper_functions.rasterization import rasterize_pdf

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def find_page_range_by_section_number(pdf_path: str, section_number: str) -> set[str]:
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)
    # pattern = re.compile(rf"\b{re.escape(section_number)}\b")
    pattern = re.compile(rf"\b{re.escape(section_number)}\s*-\s*\d+\b")

    page_set = set[str]()

    for i in range(num_pages):
        text = reader.pages[i].extract_text() or ""
        if pattern.search(text):
            page_set.add(str(i))

    if not page_set:
        return None

    sorted_pages = sorted([int(page) for page in page_set])
    return sorted_pages

class SectionLocatorResult(BaseModel):
    contains_section_start: bool = Field(description="True if this chunk contains the start of the section.")
    estimated_start_page_offset: Optional[int] = Field(default=None, description="0-based page offset within this chunk where the section appears to start.")
    confidence: float = Field(description="Model confidence from 0 to 1 in the detection.")
    notes: Optional[str] = Field(default=None, description="Any extra comments or uncertainty.")

def locate_section_in_chunk(
    chunk_text: str,
    section_number: str,
    section_title: str
) -> SectionLocatorResult:
    completion = client.beta.chat.completions.parse(
        model="gpt-4.1",
        response_format=SectionLocatorResult,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are helping locate CSI spec sections in a construction project manual. "
                    "You are given the text from a range of pages. "
                    "Your job is ONLY to determine whether this chunk contains the *start* of a specific section.\n\n"
                    "The target section is:\n"
                    f"  Section Number: {section_number}\n"
                    f"  Section Title: {section_title}\n\n"
                    "Look for typical CSI-style headings such as:\n"
                    "- 'SECTION 042000 UNIT MASONRY'\n"
                    "- '042000 UNIT MASONRY'\n"
                    "- Or visually similar variants.\n\n"
                    "If you believe the start of the section is present, set contains_section_start to true and "
                    "estimate the 0-based page offset within this chunk where that start appears "
                    "(0 for first page of chunk, 1 for second, etc.). "
                    "Otherwise, set contains_section_start to false and estimated_start_page_offset to null."
                ),
            },
            {
                "role": "user",
                "content": chunk_text,
            },
        ],
        temperature=0.0,
    )
    return completion.choices[0].message.parsed

def find_section_page_range_ai(
    pdf_path: str,
    section_number: str,
    section_title: str,
    chunk_size: int = 15
) -> Optional[Tuple[int, int]]:

    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)

    start_page_global = None

    # 1) Find start using chunk-level scanning
    for chunk_start in range(0, num_pages, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, num_pages - 1)

        # Build chunk text
        parts = []
        for i in range(chunk_start, chunk_end + 1):
            text = reader.pages[i].extract_text() or ""
            parts.append(f"\n\n--- PAGE {i+1} ---\n{text}")
        chunk_text = "\n".join(parts)

        result = locate_section_in_chunk(
            chunk_text=chunk_text,
            section_number=section_number,
            section_title=section_title,
        )

        if result.contains_section_start and result.estimated_start_page_offset is not None:
            start_page_global = chunk_start + result.estimated_start_page_offset
            break

    if start_page_global is None:
        return None

    # 2) Heuristic for end: use same logic as regex (next SECTION xxxx)
    next_section_regex = re.compile(r"SECTION\s+0?\d{5}", re.IGNORECASE)
    end_page = num_pages - 1
    for j in range(start_page_global + 1, num_pages):
        text = reader.pages[j].extract_text() or ""
        if next_section_regex.search(text):
            end_page = j - 1
            break

    return (start_page_global, end_page)

def robust_find_section_page_range(
    pdf_path: str,
    section_number: str,
    section_title: str
) -> Optional[Tuple[int, int]]:

    # First try regex
    regex_result = find_page_range_by_section_number(
        pdf_path=pdf_path,
        section_number=section_number,
    )
    if regex_result is not None:
        return regex_result

    # Fallback: AI
    ai_result = find_section_page_range_ai(
        pdf_path=pdf_path,
        section_number=section_number,
        section_title=section_title,
        chunk_size=15,  # tune as needed
    )
    return ai_result

def extract_pages_text(pdf_path: str, pages: list[int]) -> str:
    reader = PdfReader(pdf_path)
    parts = []
    for i in sorted(set(pages)):
        page = reader.pages[i]
        text = page.extract_text() or ""
        parts.append(f"\n==== PAGE {i} ====\n{text}")
    return "\n".join(parts)

class SpecRequirement(BaseModel):
    clause_id: str = Field(description="Short label like '3.6.B' or 'PART 2 - MATERIALS - A'")
    requirement: str = Field(description="Plain-language requirement text")
    requirement_type: str = Field(description="Category such as 'materials', 'installation', 'testing', 'submittals', 'warranty'")
    critical: bool = Field(description="True if non-compliance would be a major risk or code/contract violation")

class SectionSpecSummary(BaseModel):
    section_number: str
    section_title: str
    key_requirements: list[SpecRequirement]
    referenced_sections: list[str] = Field(description="Other section numbers explicitly referenced", default=[])
    risks_or_gotchas: list[str] = Field(default=[])
    open_questions: list[str] = Field(default=[])

async def extract_section_requirements(
    section_text: str,
    section_number: str,
    section_title: str = ""
) -> SectionSpecSummary:
    response = await client.beta.chat.completions.parse(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert construction specification analyst. "
                    "Your job is to extract and categorize all key requirements from a CSI specification section.\n\n"
                    "For each requirement, identify:\n"
                    "- The clause ID (e.g., '1.3.A', 'PART 2 - 2.1.B', '3.4')\n"
                    "- The actual requirement in clear language\n"
                    "- The type (materials, installation, testing, submittals, warranty, quality control, etc.)\n"
                    "- Whether it's critical (code requirement, safety issue, major cost/schedule impact)\n\n"
                    "Also extract:\n"
                    "- Any references to other specification sections\n"
                    "- Potential risks or 'gotchas' (ambiguities, strict timelines, special conditions)\n"
                    "- Any questions or uncertainties you notice\n\n"
                    "Focus on actionable requirements that a contractor would need to comply with."
                )
            },
            {
                "role": "user",
                "content": f"Section {section_number}: {section_title}\n\n{section_text}"
            }
        ],
        response_format=SectionSpecSummary,
    )

    return response.choices[0].message.parsed

async def analyze_section(pdf_path: str, section_number: str, section_title: str = "") -> Optional[SectionSpecSummary]:
    # Step 1: Find the pages containing this section
    pages = find_page_range_by_section_number(pdf_path, section_number)

    if not pages or len(pages) == 0:
        logger.warning(f"No pages found for section {section_number}")
        return None

    logger.info(f"Found section {section_number} on {len(pages)} pages: {pages}")

    # Step 2: Extract text from those pages
    section_text = extract_pages_text(pdf_path, pages)

    logger.info(f"Extracted {len(section_text)} characters from section {section_number}")

    # Step 3: Use AI to extract requirements
    summary = await extract_section_requirements(section_text, section_number, section_title)

    logger.info(f"Extracted {len(summary.key_requirements)} requirements from section {section_number}")

    return summary

async def analyze_all_sections(pdf_path: str, sections: list[dict]) -> dict:

    results = {}
    for section in sections:
        summary = await analyze_section(
            pdf_path,
            section["section_number"],
            section["section_title"]
        )
        results[section["section_number"]] = summary

    return results

section_number = "042000"
section_title = "UNIT MASONRY"
pdf_path = "example_spec.pdf"

result = asyncio.run(analyze_section(pdf_path, section_number, section_title))
print(result)
