import base64, json, os, fitz, logging
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from classes.s3_buckets import S3Bucket
from classes.pdf_page_converter import PDFPageConverter

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TableOfContentsDetection(BaseModel):
    is_toc_page: bool = Field(
        description=(
            "True if the page is part of a table-of-contents style listing of divisions/sections. "
            "False if the page is not part of a table-of-contents style listing of divisions/sections. "
        ),
        default=False
    )

# I'm unsure if this is needed, I'm hoping it will increase accuracy
async def table_of_contents_detection_ai(spec_page: bytes) -> bool:
    response = await client.beta.chat.completions.parse(
        model="gpt-4.1",
        response_format=TableOfContentsDetection,
        messages=[
            {
                "role": "system",
                "content": (
                    "Determine whether or not this page is part of a table-of-contents style listing of divisions/sections. "
                    "Division numbers are always in CSI Master Format. "
                    "Divison numbers are always in the format '03', '09', '12', '21', etc. "
                    "Sections are always in the format '220505', '262913.03', '013300a', etc. "
                    "If you see the word 'Table of Contents', assume it's True. "
                    "If you are unsure, return False."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze the following pages of a spec sheet and detect which CSI divisions are present."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(spec_page).decode('utf-8')}"}}
                ]
            }
        ]
    )
    return json.loads(json.dumps(response.choices[0].message.parsed.model_dump()))

async def table_of_contents_detection(spec_id: str) -> list[int]:
    try:
        s3 = S3Bucket()
        pdf_page_converter = PDFPageConverter()

        original_pdf = s3.get_original_pdf(spec_id)

        if original_pdf['status_code'] != 200:
            raise ValueError(original_pdf['data'])

        doc = fitz.open(stream=original_pdf['data'], filetype="pdf")

        toc_indices: list[int] = []
        for page in s3.get_converted_pages_generator(spec_id):
            if page['bytes']:
                res = await table_of_contents_detection_ai(page['bytes'])
                is_toc = res['is_toc_page']
            else:
                bytes = pdf_page_converter.rasterize_page(doc, page['page_index'])
                res = await table_of_contents_detection_ai(bytes)
                is_toc = res['is_toc_page']

            if not is_toc and len(toc_indices) == 0:
                logger.info(f"Skipping Page. Not a TOC. Page: {page['page_index']}")
                continue
            elif is_toc:
                toc_indices.append(page['page_index'])
                logger.info(f"Found TOC. Continuing Scan. Page: {page['page_index']}")
            else:
                logger.info(f"End of TOC detected. Stopping Scan. Page: {page['page_index']}")
                break

        return {
            "toc_indices": toc_indices,
            "status_code": 200 if len(toc_indices) > 0 else 404
        }
    except Exception as e:
        logger.error(f"Error getting table of contents from S3 bucket: {e}")
        return {
            "toc_indices": [],
            "status_code": 500,
            "error": str(e)
        }

# import asyncio
# if __name__ == "__main__":
#     # spec_id = "c3dbbba7-b6c8-4046-95d8-64d18edf90bf"
#     spec_id = "eac1e6d2-119c-4add-afdc-b42405f944a9"
#     print(asyncio.run(table_of_contents_detection(spec_id)))
