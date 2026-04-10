import re
import asyncio
import fitz
from classes import PDFPageConverter, S3Bucket
from concurrent.futures import ProcessPoolExecutor
from csi_masterformat import divisions_and_sections
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Build a flat set of all known MasterFormat section numbers for O(1) lookup


def build_known_sections() -> set:
    known = set()
    for div_sections in divisions_and_sections.values():
        known.update(div_sections.keys())
    return known


KNOWN_SECTIONS = build_known_sections()

# Regex is still used to find candidates, but every match is validated against KNOWN_SECTIONS
# Finds patterns such as 003132, 00 31 32, 00-31-32, 00.31.32, 003132.12, 003132.12a, 00 31 32.12b, etc.
CANDIDATE_PATTERN = re.compile(
    r"(?<![0-9.])"  # added . to the lookbehind to prevent false positives
    r"(?:(?:0[0-9]|[1-4][0-9]|49)(?:[\s.\-]?\d{2}){2})"
    r"(?:\.\d{1,2})?[A-Za-z]?"
    r"(?![0-9])"
)


def normalize_section_number(section: str) -> str:
    """Normalize any format (00 31 32, 00-31-32, 003132) to compact form (003132)."""
    clean = re.sub(r"[\s\-]", "", section)

    match = re.match(
        r"^(\d{2})\.?(\d{2})\.?(\d{2})(?:\.(\d+))?([a-zA-Z]?)$", clean)
    if match:
        base = match.group(1) + match.group(2) + match.group(3)
        subsection = match.group(4)
        letter = match.group(5)

        result = base
        if subsection:
            result += "." + subsection
        if letter:
            result += letter
        return result
    return None


def is_valid_section(raw_match: str) -> str:
    """Normalize a regex match and return it only if it's a known MasterFormat section number."""
    normalized = normalize_section_number(raw_match)
    if normalized and normalized in KNOWN_SECTIONS:
        return normalized

    # Also check base6 without suffix (e.g. 003132 from 003132.12)
    if normalized and len(normalized) > 6:
        base = normalized[:6]
        if base in KNOWN_SECTIONS:
            return normalized

    # If the normalized is not a known section, check if the first 4 characters are a known section
    elif normalized:
        base = normalized[:4]
        for section in KNOWN_SECTIONS:
            if section.startswith(base):
                logger.info(f"Found known section: {normalized}")
                return normalized
    return None


def flatten(section_numbers: list[list[str]]):
    flattened_list = []
    for numbers in section_numbers:
        flattened_list.extend(numbers)
    return flattened_list


def worker_scan_shard(spec_id: str, start_index: int, end_index: int) -> dict:
    async def _run():
        s3 = S3Bucket()
        converter = PDFPageConverter()
        section_numbers = {page_index: []
                           for page_index in range(start_index, end_index)}

        async with s3.s3_client() as s3_client:
            for page_index in range(start_index, end_index):
                key = f"{spec_id}/original_pages/page_{page_index:04d}.pdf"
                response = await s3_client.get_object(Bucket=s3.bucket_name, Key=key)
                page_bytes = await response["Body"].read()

                for page in converter.pdf_page_converter_generator(pdf=page_bytes):
                    text = page.get("text") or ""
                    if not text:
                        continue
                    for match in CANDIDATE_PATTERN.finditer(text):
                        validated = is_valid_section(match.group(0))
                        if validated:
                            section_numbers[page_index].append(validated)

        return section_numbers

    return asyncio.run(_run())


def contiguous_page_divider(page_indices: dict[str, list[int]]) -> dict:
    dict_indices: dict[list[int]] = {section: {
        "single": [],
        "multi": [],
        "title": divisions_and_sections.get(section[0:2], {}).get(section, "Undocumented Section Number (MSF2020)")
    } for section in page_indices.keys()}

    if not page_indices:
        return dict_indices

    for section, indices in page_indices.items():
        if not indices:
            continue
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


def section_page_dict(section_numbers: dict):
    section_page_dict = {}

    for page_index, section_numbers in section_numbers.items():
        for section_number in section_numbers:
            normalized_section_number = normalize_section_number(
                section_number)
            if section_page_dict.get(normalized_section_number):
                if page_index in section_page_dict[normalized_section_number]:
                    continue
                else:
                    section_page_dict[normalized_section_number].append(
                        page_index)
            else:
                section_page_dict[normalized_section_number] = [page_index]

    results = contiguous_page_divider(section_page_dict)
    return results

# Nest key:value into divisions as master key ----> {division: {section: [page_indices]}}
def division_parser(section_pages: dict) -> dict:
    divisions_dict = {}
    for section, page_indices in section_pages.items():
        div_key = section[0:2]
        if div_key not in divisions_dict:
            divisions_dict[div_key] = {}
        divisions_dict[div_key][section] = page_indices
    return divisions_dict


async def section_pages_detection(spec_id: str, s3: S3Bucket, s3_client: any, workers: int = 6) -> dict:
    total_pages = await s3.get_original_page_count_with_client(spec_id, s3_client)
    print("TOTAL PAGES: ", total_pages)

    divider = total_pages / workers
    shards = [(int(divider * i), int(divider * (i + 1)))
              for i in range(workers)]
    loop = asyncio.get_running_loop()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            loop.run_in_executor(executor, worker_scan_shard,
                                 spec_id, start_index, end_index)
            for start_index, end_index in shards
        ]
        results = await asyncio.gather(*futures)
        flattened_results = {k: v for d in results for k, v in d.items()}

        divisions = division_parser(section_page_dict(flattened_results))

        return {
            "total_divisions": len(divisions.keys()),
            "total_sections": len(flattened_results.keys()),
            "divisions_and_sections": divisions
        }
