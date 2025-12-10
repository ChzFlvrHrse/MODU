from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
import os, logging, re, sys, base64, json, asyncio, fitz

sys.path.insert(0, str(Path(__file__).parent.parent))
from classes.pdf_page_converter import PDFPageConverter
from classes.typed_dicts import HybridPage
from classes.s3_buckets import S3Bucket

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pdf_page_converter = PDFPageConverter()
s3 = S3Bucket()

class SectionSpecList(BaseModel):
    pages: list[int] = Field(description="All pages that contain the section number and/or section title. Should be left empty if the section number and/or section title is not present.")

def spec_section_detection_text(spec_pages: list[HybridPage], section_number: str, section_title: str) -> set[str]:
    pattern_number = re.compile(rf"\b{re.escape(section_number)}\b")
    pattern_title = re.compile(rf"\b{re.escape(section_title)}\b")
    # pattern = re.compile(rf"\b{re.escape(section_number)}\s*-\s*\d+\b")

    page_set = []

    for page in spec_pages:
        if pattern_number.search(page['text']) or pattern_title.search(page['text']):
            page_set.append(page['page_index'])

    return sorted([int(page) for page in page_set])

async def spec_section_detection_ai(spec_pages: list[HybridPage], section_number: str, section_title: str) -> list[int]:
    detected_pages = []

    for image_page in spec_pages:
        response = await client.beta.chat.completions.parse(
            model="gpt-4.1",
            response_format=SectionSpecList,
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert construction specification analyst. "
                        "Given a page image of a spec sheet, your job is to detect the image contains the section number and/or section title. "
                        "Return the index of the page if the section number and/or section title is present."
                        f"The section number is: {section_number}"
                        f"The section title is: {section_title}"
                        f"The page index is: {image_page['page_index']}"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are an expert construction specification analyst. "
                                "Given a page image of a spec sheet, your job is to detect ALL pages that contain the section number and/or section title. "
                                "Return every page where the section number and/or section title is present."
                                f"The section number is: {section_number}"
                                f"The section title is: {section_title}"
                                f"The page index is: {image_page['page_index']}"
                            )
                        },
                        {
                            "type": "text",
                            "text": f"PAGE_INDEX: {image_page['page_index']}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64.b64encode(image_page['bytes']).decode('utf-8')}"}
                        }
                    ]
                }
            ]
        )
        detected_pages.extend(json.loads(json.dumps(response.choices[0].message.parsed.model_dump()))["pages"])

    return list(set(detected_pages))

async def spec_section_pages(spec_pages: list[HybridPage], section_number: str, section_title: str) -> list[int]:
    all_text_pages = [{"page_index": page['page_index'], "text": page['text']} for page in spec_pages if page['text']]
    all_image_pages = [{"page_index": page['page_index'], "bytes": page['bytes']} for page in spec_pages if page['bytes']]

    if all_text_pages:
        detected_text_pages = spec_section_detection_text(all_text_pages, section_number, section_title)
    else:
        detected_text_pages = []

    if all_image_pages:
        detected_image_pages = await spec_section_detection_ai(all_image_pages, section_number=section_number, section_title=section_title)
    else:
        detected_image_pages = []

    return list(set([*detected_text_pages, *detected_image_pages]))

async def section_spec_detection(
    spec_id: str,
    section_number: str,
    section_title: str,
    batch_size: int = 20,
    start_index: int = 0,
    end_index: int = None
) -> list[int]:
    detected_pages: list[int] = []
    batch: list[HybridPage] = []

    if batch_size > 20:
        raise ValueError("Batch size must be less than or equal to 20")
    if start_index < 0:
        raise ValueError("Start index must be greater than or equal to 0")
    if end_index is not None and end_index < 0:
        raise ValueError("End index must be greater than or equal to 0")
    if end_index is not None and end_index < start_index:
        raise ValueError("End index must be greater than or equal to start index")

    if end_index is None:
        end_index = s3.get_page_count(spec_id)

    try:
        for page in s3.get_converted_pages_generator(spec_id, start_index=start_index, end_index=end_index):
            batch.append(page)
            if len(batch) >= batch_size:
                detected_pages.extend(await spec_section_pages(batch, section_number=section_number, section_title=section_title))
                logger.info(f"Detected pages: {detected_pages}, Total pages: {len(detected_pages)}")
                batch = []
        if batch:
            detected_pages.extend(await spec_section_pages(batch, section_number=section_number, section_title=section_title))
            logger.info(f"Detected pages: {detected_pages}")
    except Exception as e:
        logger.error(f"Error getting converted pages from S3 bucket: {e}")
        return []

    return detected_pages

# pdf_path = "example_spec.pdf"
# section_number = "013113"
# section_title = "COORDINATION DRAWINGS"
# batch_size = 5
# dpi = 200
# grayscale = False
# start_page = 9
# end_page = 9

# rasterize = hybrid_pdf(pdf_path, dpi=dpi, grayscale=grayscale, start_index=start_page, end_index=end_page)
# for page in rasterize:
#     print(page)
