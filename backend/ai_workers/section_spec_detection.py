from dotenv import load_dotenv
from openai import AsyncOpenAI
import os, logging, re, asyncio
from pydantic import BaseModel, Field

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

# Sort contiguous page indices into arrays by length
def contiguous_page_divider(page_indices: list[int]) -> dict[str, list]:
    if not page_indices:
        return []

    dict_indices: dict[list[int]] = {
        "single": [],
        "multi": []
    }
    indices: list[list[int]] = [[page_indices[0]]]
    for p in page_indices[1:]:
        current_series = indices[-1]
        if p == current_series[-1] + 1:
            current_series.append(p)
        else:
            indices.append([p])

    for i in indices:
        if len(i) == 1:
            dict_indices['single'].extend(i)
        else:
            dict_indices['multi'].append(i)

    return dict_indices

class PageClassification(BaseModel):
    is_primary: bool = Field(
        description="Whether the page is part of the primary section body or is just referential (TOC, cross-references, mentions)"
    )
    reasoning: str = Field(
        description="Brief explanation of how the decision was made"
    )

async def classify_primary_or_context_segments_ai(pages_dict: dict, max_in_flight: int = 6) -> dict:
    multi_pages: list[list[dict]] = pages_dict["multi"]
    single_pages: list[dict] = pages_dict["single"]
    section_number: str = pages_dict["section_number"]

    primary_pages: list[dict] = []
    context_pages: list[dict] = []

    def build_messages(segment_pages: list[dict]) -> list[dict]:
        content_blocks = [
            {
                "type": "text",
                "text": (
                    "You are classifying page SEGMENTS from a construction specification.\n\n"
                    "Each segment is a contiguous group of pages.\n\n"
                    "Classify the segment as:\n"
                    f"- PRIMARY: contains the actual section body for section {section_number} "
                    "(requirements, products, execution; often PART 1/2/3 language)\n"
                    "- CONTEXT: only references the section (TOC, cross-references, listings)\n\n"
                    "Do NOT extract data. Only classify.\n"
                    "Return JSON that matches the schema.\n"
                ),
            }
        ]

        for page in segment_pages:
            text = page.get("text") or ""
            # Optional: truncate to avoid huge prompts
            # text = text[:8000]
            content_blocks.append(
                {
                    "type": "text",
                    "text": (
                        f"===== PAGE {page['page_index']} START =====\n"
                        f"{text}\n"
                        f"===== PAGE {page['page_index']} END =====\n"
                    ),
                }
            )

        return [{"role": "user", "content": content_blocks}]

    sem = asyncio.Semaphore(max_in_flight)

    async def classify_segment(segment_pages: list[dict]) -> tuple[bool, list[dict]]:
        async with sem:
            res = await client.beta.chat.completions.parse(
                model="gpt-4.1",
                response_format=PageClassification,
                messages=build_messages(segment_pages),
                temperature=0.0,
            )
            parsed = res.choices[0].message.parsed
            return parsed.is_primary, segment_pages

    # Classify multi segments concurrently
    multi_results = await asyncio.gather(*[classify_segment(seg) for seg in multi_pages])

    for is_primary, seg_pages in multi_results:
        if is_primary:
            # Only get page indices
            primary_pages.extend([page['page_index'] for page in seg_pages])
        else:
            context_pages.extend([page['page_index'] for page in seg_pages])

    # Optional: only classify singles if you want (often cheaper to treat them as context by default)
    # If you want to classify singles too, do it like this:
    # single_results = await asyncio.gather(*[classify_segment([p]) for p in single_pages])
    # for is_primary, seg_pages in single_results:
    #     (primary_pages if is_primary else context_pages).extend(seg_pages)

    # Default behavior: treat singles as context (unless you decide otherwise)
    context_pages.extend([page['page_index'] for page in single_pages])

    return {
        "primary": primary_pages,
        "context": context_pages,
        "section_number": section_number
    }

async def primary_context_classification(spec_id: str, section_pages: list[int], s3_client: any, section_number: str) -> dict:
    s3 = S3Bucket()
    sorted_pages = sorted(section_pages, key=lambda x: x)

    all_indices = contiguous_page_divider(sorted_pages)

    single_pages: list[int] = all_indices['single']
    multi_pages: list[list[int]] = all_indices['multi']

    if single_pages:
        single_texts = await asyncio.gather(
            *[s3.get_text_page_with_client(spec_id=spec_id, index=page, s3_client=s3_client) for page in single_pages]
        )
        single_pages_text: list[dict] = [{"page_index": page, "text": text} for page, text in zip(single_pages, single_texts)]

    multi_pages_text: list[list[dict]] = []
    if multi_pages:
        for multi_page in multi_pages:
            multi_page_text: list[dict] = []
            pages = await asyncio.gather(*[s3.get_text_page_with_client(spec_id=spec_id, index=page, s3_client=s3_client) for page in multi_page])
            for index, page in enumerate(multi_page):
                multi_page_text.append({
                    "page_index": page,
                    "text": pages[index]
                })
            multi_pages_text.append(multi_page_text)

    res = {
        "multi": multi_pages_text,
        "single": single_pages_text,
        "section_number": section_number
    }

    return await classify_primary_or_context_segments_ai(res)

if __name__ == "__main__":
    import asyncio
    async def main():
        s3 = S3Bucket()
        spec_id = "1ca7077a-ac58-4f5a-9b40-f6847ff235e2"
        section_number = "013113"
        section_pages = [76, 89, 90, 91, 92, 93, 94, 95, 96, 103]
        async with s3.s3_client() as s3_client:
            print(await primary_context_classification(spec_id, section_pages, s3_client, section_number))
    asyncio.run(main())
