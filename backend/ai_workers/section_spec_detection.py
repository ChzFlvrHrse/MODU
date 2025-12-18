from dotenv import load_dotenv
from openai import AsyncOpenAI
import os, logging, re, asyncio
from pydantic import BaseModel, Field
from concurrent.futures import ProcessPoolExecutor

from classes.s3_buckets import S3Bucket

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def split_section(section: str) -> tuple[str, str]:
    section = section.strip()
    if len(section) < 6 or not section[:6].isdigit():
        raise ValueError(f"Section must start with 6 digits: {section}")

    return section[:6], section[6:]

def base_variants(base6: str) -> list[str]:
    a, b, c = base6[:2], base6[2:4], base6[4:]
    return [
        rf"{base6}",                    # 003132
        rf"{a}\s*{b}\s*{c}",             # 00 31 32 (or 003132 with spaces)
        rf"{a}[-\.]{b}[-\.]{c}",         # 00-31-32 or 00.31.32
    ]

def suffix_pattern(suffix: str) -> str:
    if not suffix:
        return ""

    if suffix.startswith("."):
        # .12 → allow whitespace around dot
        return rf"\s*\.\s*{re.escape(suffix[1:])}"

    # letter / alphanumeric suffix (b, a, A1, etc.)
    return rf"\s*{re.escape(suffix)}"

def build_section_patterns(section_pages: list[str]) -> dict[str, list[str]]:
    patterns: dict[str, list[str]] = {}
    for section in section_pages:
        base6, suffix = split_section(section)
        base_pats = base_variants(base6)
        suf_pat = suffix_pattern(suffix)
        patterns[f"{section}"] = []
        for b in base_pats:
            full = rf"{b}{suf_pat}"
            patterns[f"{section}"].append(rf"(?<!\w){full}(?!\w)")
    return patterns

def worker_scan_shard(spec_id: str, start_index: int, end_index: int, section_pages: list[str]) -> dict:
    async def _run():
        s3 = S3Bucket()
        compiled_patterns = build_section_patterns(section_pages)
        detected_pages: dict[str, list[int]] = {sec: [] for sec in compiled_patterns.keys()}

        async with s3.s3_client() as s3_client:
            gen = s3.get_converted_pages_generator_with_client(
                spec_id, s3_client, start_index=start_index, end_index=end_index
            )
            # do work here (regex etc)
            async for page in gen:

                text = page.get("text") or ""
                if not text:
                    continue

                page_index = page["page_index"]
                for section, patterns in compiled_patterns.items():
                    if any(re.search(pat, text, re.IGNORECASE) for pat in patterns):
                        detected_pages[section].append(page_index)
            return detected_pages

    return asyncio.run(_run())

async def run_shards(spec_id: str, section_pages: list[str], total_pages: int) -> dict:
    divider = total_pages / 4
    shards = [(int(divider * i), int(divider * (i + 1))) for i in range(4)]
    loop = asyncio.get_running_loop()

    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            loop.run_in_executor(executor, worker_scan_shard, spec_id, start_index, end_index, section_pages)
            for start_index, end_index in shards
        ]
        return await asyncio.gather(*futures)

def merge_results(section_pages: list[dict]) -> dict:
    merged_results = {}
    for section, page_indices in section_pages[0].items():
        for i in range(1, len(section_pages)):
            page_indices.extend(section_pages[i][section])
        merged_results[section] = page_indices
    return merged_results

async def section_spec_detection(
    spec_id: str,
    section_numbers: list[str],
    s3: S3Bucket,
    s3_client: any,
    start_index: int = 0,
    end_index: int = None,
) -> dict[str, list[int]]:

    if start_index < 0:
        raise ValueError("Start index must be greater than or equal to 0")
    if end_index is not None and end_index < 0:
        raise ValueError("End index must be greater than or equal to 0")
    if end_index is not None and end_index < start_index:
        raise ValueError("End index must be greater than or equal to start index")

    page_count = await s3.get_original_page_count_with_client(spec_id, s3_client)

    if end_index is None:
        end_index = await s3.get_original_page_count_with_client(spec_id, s3_client)
    else:
        end_index = min(end_index, page_count)

    results = await run_shards(spec_id, section_numbers, page_count)
    return merge_results(results)

# ---------------------------------------------------------------- Divider ------------------------------------------------------------

# Sort contiguous page indices into arrays by length
def contiguous_page_divider(page_indices: dict[str, list[int]]) -> dict:
    dict_indices: dict[list[int]] = {section: {
        "single": [],
        "multi": []
    } for section in page_indices.keys()}

    if not page_indices:
        return dict_indices

    for section, indices in page_indices.items():
        indices_list: list[list[int]] = [[indices[0]]]
        for p in indices[1:]:
            current_series = indices_list[-1]
            if p == current_series[-1] + 1:
                current_series.append(p)
            else:
                indices_list.append([p])

        for i in indices_list:
            if len(i) == 1:
                dict_indices[section]["single"].extend(i)
            else:
                dict_indices[section]["multi"].append(i)

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
        "context": context_pages
    }

async def primary_context_classification(
    spec_id: str,
    section_pages: dict[str, list[int]],
    s3: S3Bucket,
    s3_client: any,
    s3_max_in_flight: int = 25,   # throttle S3 reads
    ai_max_in_flight: int = 6,    # your classifier already throttles internally
) -> dict[str, dict]:
    all_indices = contiguous_page_divider(section_pages)

    results: dict[str, dict] = {}
    sem = asyncio.Semaphore(s3_max_in_flight)

    async def get_text(page_index: int) -> str:
        async with sem:
            return await s3.get_text_page_with_client(
                spec_id=spec_id,
                index=page_index,
                s3_client=s3_client,
            )

    for section, indices in all_indices.items():
        single_pages: list[int] = indices["single"]
        multi_pages: list[list[int]] = indices["multi"]

        # ---- Singles ----
        single_pages_text: list[dict] = []
        if single_pages:
            single_texts = await asyncio.gather(*[get_text(p) for p in single_pages])
            single_pages_text = [{"page_index": p, "text": t} for p, t in zip(single_pages, single_texts)]

        # ---- Multi runs ----
        multi_pages_text: list[list[dict]] = []
        if multi_pages:
            run_texts = await asyncio.gather(
                *[asyncio.gather(*[get_text(p) for p in run]) for run in multi_pages]
            )
            for run_pages, texts in zip(multi_pages, run_texts):
                multi_pages_text.append([{"page_index": p, "text": t} for p, t in zip(run_pages, texts)])

        res = {
            "multi": multi_pages_text,
            "single": single_pages_text,
            "section_number": section,
        }

        # If you want, you can throttle section-level AI calls too,
        # but your classify_primary_or_context_segments_ai already throttles segments.
        results[section] = await classify_primary_or_context_segments_ai(res, max_in_flight=ai_max_in_flight)

    return results

# if __name__ == "__main__":
#     import asyncio
#     async def main():
#         s3 = S3Bucket()
#         spec_id = "1ca7077a-ac58-4f5a-9b40-f6847ff235e2"
#         section_number = "013113"
#         section_pages = [76, 89, 90, 91, 92, 93, 94, 95, 96, 103]
#         async with s3.s3_client() as s3_client:
#             print(await primary_context_classification(spec_id, section_pages, s3_client, section_number))
#     asyncio.run(main())
