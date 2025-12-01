import os, logging, re
from typing import Optional, Tuple
from pypdf import PdfReader
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from division_detection_result import division_detection_result

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SECTION_HEADER_PATTERN = r"(SECTION\s+)?0*{sec}"

class SectionLocatorResult(BaseModel):
    contains_section_start: bool = Field(description="True if this chunk contains the start of the section.")
    estimated_start_page_offset: Optional[int] = Field(default=None, description="0-based page offset within this chunk where the section appears to start.")
    confidence: float = Field(description="Model confidence from 0 to 1 in the detection.")
    notes: Optional[str] = Field(default=None, description="Any extra comments or uncertainty.")

def find_section_page_range_regex(
    pdf_path: str,
    section_number: str,
    section_name: Optional[str] = None,
    search_start_page: int = 0
) -> Optional[Tuple[int, int]]:

    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)

    # Base pattern on section number
    sec = re.escape(section_number)
    pattern = SECTION_HEADER_PATTERN.format(sec=sec)

    # Optionally bias by section_name (but don’t require it)
    if section_name:
        name = re.escape(section_name)
        pattern = pattern + r".{0,80}" + name  # name within ~80 chars

    regex = re.compile(pattern, re.IGNORECASE | re.VERBOSE)

    start_page = None
    for i in range(search_start_page, num_pages):
        text = reader.pages[i].extract_text() or ""
        if regex.search(text):
            start_page = i
            break

    if start_page is None:
        return None

    # Heuristic for end: look for next 'SECTION xxxxx' after start_page
    next_section_regex = re.compile(r"SECTION\s+0?\d{5}", re.IGNORECASE)
    end_page = num_pages - 1
    for j in range(start_page + 1, num_pages):
        text = reader.pages[j].extract_text() or ""
        if next_section_regex.search(text):
            end_page = j - 1
            break

    return (start_page, end_page)
