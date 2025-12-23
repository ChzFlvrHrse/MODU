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
        # regex_pattern = r"(?<![\d.-])(?:(?:0[0-9]|[1-4][0-9]|50)(?:[\s.-]?\d{2}){2}|(?:0[0-9]|[1-4][0-9]|50)\d{3})(?:\.\d+)?[A-Za-z]?(?!\d)"
        regex_pattern = r"(?<![\d.-])(?!\d{4}[./-]\d{2}[./-]\d{2})(?:(?:0[0-9]|[1-4][0-9]|50)(?:[\s.-]?\d{2}){2}|(?:0[0-9]|[1-4][0-9]|50)\d{3})(?:\.\d+)?[A-Za-z]?(?!\d)"
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
                        # section_numbers.append(match.group(0))
                        section_numbers[page_index].append(match.group(0))

            return section_numbers

    return asyncio.run(_run())

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
        return await asyncio.gather(*futures)

if __name__ == "__main__":
    s3 = S3Bucket()
    spec_id = "1ca7077a-ac58-4f5a-9b40-f6847ff235e2"
    async def main():
        async with s3.s3_client() as s3_client:
            results = await run_shards(spec_id, s3, s3_client, workers=4)
        return results
    print(asyncio.run(main()))
