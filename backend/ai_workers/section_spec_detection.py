import os, logging, re
from dotenv import load_dotenv
from openai import AsyncOpenAI

from classes.s3_buckets import S3Bucket

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def section_spec_detection(
    spec_id: str,
    section_number: str,
    s3: S3Bucket,
    s3_client: any,
    start_index: int = 0,
    end_index: int = None,
) -> list[int]:

    if start_index < 0:
        raise ValueError("Start index must be greater than or equal to 0")
    if end_index is not None and end_index < 0:
        raise ValueError("End index must be greater than or equal to 0")
    if end_index is not None and end_index < start_index:
        raise ValueError("End index must be greater than or equal to start index")

    detected_pages: list[int] = []
    compiled_patterns: list[re.Pattern] = [re.compile(rf"\b{re.escape(section_number)}\b")]

    if end_index is None:
        page_count = await s3.get_original_page_count_with_client(spec_id, s3_client)
        end_index = page_count

    async for page in s3.get_converted_pages_generator_with_client(
        spec_id, s3_client, start_index=start_index, end_index=end_index
    ):
        text = page.get("text") or ""
        if not text:
            continue

        for pat in compiled_patterns:
            if pat.search(text):
                detected_pages.append(page["page_index"])
                break

    return detected_pages

# spec_id = "0ec5802c-4df5-416a-b435-409daf26db9e"
# section_number = "013524"
# section_title = "Safety"
# batch_size = 5
# dpi = 200
# grayscale = False
# start_page = 9
# # end_page = 9

# asyncio.run(section_spec_detection(spec_id=spec_id, section_number=section_number))
