import re, asyncio
from classes.s3_buckets import S3Bucket
from concurrent.futures import ProcessPoolExecutor

def flatten(section_numbers: list[list[str]]):
    flattened_list = []
    for numbers in section_numbers:
        flattened_list.extend(numbers)
    return flattened_list

def worker_scan_shard(spec_id: str, start_index: int, end_index: int) -> list[dict]:
    async def _run():
        s3 = S3Bucket()

        regex_pattern = (
            r"(?<![0-9])"                                           # Not preceded by digit
            r"(?!\d{2}[-./]\d{4})"                                   # Not XX-YYYY (date format like 22-0120)
            r"(?!\d{4}[\n\r])"                                       # Not XXXX\n
            r"(?!(?:19|20)\d{2}[-./]\d{2})"                         # Not YYYY-MM
            r"(?!\d{2}[-./]\d{2}[-./](?:19|20)\d{2})"              # Not MM-DD-YYYY
            r"(?!\d{2}[\n\r]\d{2})"                                  # Not XX\nYY (blocks 13\n21-30)
            r"(?:(?:0[0-9]|[1-4][0-9]|49)(?:[\s.-]?\d{2}){2}|"      # XX-YY-ZZ format
            r"(?:0[0-9]|[1-4][0-9]|49)\d{4})"                        # XXYYZZ format
            r"(?:\.\d{1,2})?[A-Za-z]?"                              # Optional .XX subsection
            r"(?![0-9\n\r])"                                         # Not followed by digit or newline
        )

        section_numbers: dict = {page_index: [] for page_index in range(start_index, end_index)}

        async with s3.s3_client() as s3_client:
            gen = s3.get_converted_pages_generator_with_client(
                spec_id, s3_client, start_index=start_index, end_index=end_index
            )
            # do work here (regex etc)
            async for page in gen:

                text = page.get("text") or ""
                page_index = page["page_index"]
                if not text or not page_index:
                    continue

                for match in re.finditer(regex_pattern, text):
                    if match.group(0):
                        section_numbers[page_index].append(match.group(0))

            return section_numbers

    return asyncio.run(_run())

def normalize_section_number(section: str) -> str:
    # Remove spaces and dashes only (keep dots for subsections)
    clean = re.sub(r"[\s\-]", "", section)

    # Match: 6 digits, optional dot + subsection, optional letter
    match = re.match(r"^(\d{2})\.?(\d{2})\.?(\d{2})(?:\.(\d+))?([a-zA-Z]?)$", clean)

    if match:
        base = match.group(1) + match.group(2) + match.group(3)  # xxyyzz
        subsection = match.group(4)  # .12, .13, etc.
        letter = match.group(5)  # a, b, c

        result = base
        if subsection:
            result += "." + subsection
        if letter:
            result += letter

        return result

    return None

def contiguous_page_divider(page_indices: dict[str, list[int]]) -> dict:
    dict_indices: dict[list[int]] = {section: {
        "single": [],
        "multi": []
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
            normalized_section_number = normalize_section_number(section_number)
            if section_page_dict.get(normalized_section_number):
                if page_index in section_page_dict[normalized_section_number]:
                    continue
                else:
                    section_page_dict[normalized_section_number].append(page_index)
            else:
                section_page_dict[normalized_section_number] = [page_index]

    return contiguous_page_divider(section_page_dict)

async def run_shards(spec_id: str, s3, s3_client, workers: int = 4) -> list[str]:
    total_pages = await s3.get_original_page_count_with_client(spec_id, s3_client)

    divider = total_pages / workers
    shards = [(int(divider * i), int(divider * (i + 1))) for i in range(workers)]
    loop = asyncio.get_running_loop()

    # NOTE: I'm only using 50 workers because for time. Will not be used in production.
    with ProcessPoolExecutor(max_workers=50) as executor:
        futures = [
            loop.run_in_executor(executor, worker_scan_shard, spec_id, start_index, end_index)
            for start_index, end_index in shards
        ]
        # flatten into a single dict
        results = await asyncio.gather(*futures)
        flattened_results = {k: v for d in results for k, v in d.items()}
        return section_page_dict(flattened_results)
        # return results

if __name__ == "__main__":
    s3 = S3Bucket()
    spec_id = "1ca7077a-ac58-4f5a-9b40-f6847ff235e2"
    async def main():
        async with s3.s3_client() as s3_client:
            results = await run_shards(spec_id, s3, s3_client, workers=4)
        return results
    print(asyncio.run(main()))
    # results = asyncio.run(main())
    # print(section_page_dict(results))
    # section_numbers = ["000033", "22-05-05", "2629-13.03", "01-33-00a", "02 33 00a", "03.33.00a", "03 33 00.12"]
    # for section in section_numbers:
    #     print(normalize_section_numbers(section))
