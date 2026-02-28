from typing import Any, Dict
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Callable, Type, List
from prompts import CLASSIFICATION_PROMPT
import logging
import asyncio
import time
import os
import resend
from .section_summary import section_summaries
from classes import S3Bucket, Anthropic, db, make_classification_schema

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic = Anthropic()


def send_mail(spec_id: str, completion_time: float) -> Dict:
    resend.api_key = os.getenv("RESEND_API_KEY")
    params: resend.Emails.SendParams = {
        # This is Resend's built-in test sender
        "from": "MODU <onboarding@resend.dev>",
        "to": ["nscott1010@gmail.com"],
        "subject": "MODU Classification Complete",
        # Should be dynamic for second, minute, hour, etc.
        "html": f"<strong>The MODU classification process has completed successfully for {spec_id} in {completion_time}.</strong>",
    }
    email: resend.Emails.SendResponse = resend.Emails.send(params)
    return email


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.2f} minutes"
    else:
        return f"{seconds/3600:.2f} hours"


async def save_classification_results(spec_id: str, batch_results: list[list[dict]]) -> dict[str, Any]:
    total_divisions: set[str] = set()
    total_sections: set[str] = set()
    sections_with_primary_count: int = 0
    sections_with_reference_count: int = 0
    sections_with_primary: dict[str, dict[str, List[int]]] = {}

    errors: int = 0
    failed_custom_ids = set()

    for batch in batch_results:
        for item in batch:
            custom_id = item.get('custom_id', '')

            logger.info(f"BATCH ITEM: {item}")
            if item.get('type') == 'errored':
                logger.error(f"Errored for {custom_id}: {item.get('error')}")
                errors += 1
                failed_custom_ids.add(custom_id)
                continue

            split_custom_id = custom_id.split('-')

            content = item.get('content')
            division = split_custom_id[0]
            section_number = split_custom_id[1].replace("_", ".")
            is_primary = content.get('is_primary', False)

            custom_id_length = len(split_custom_id)

            # If there are multiple pages analyzed, use the start and end index of the last page
            start_index = split_custom_id[-2] if custom_id_length == 9 else split_custom_id[-1]
            end_index = split_custom_id[-1]

            full_range = [page for page in range(
                int(start_index), int(end_index) + 1)]

            if is_primary:
                sections_with_primary_count += 1
                if division not in sections_with_primary:
                    sections_with_primary[division] = {}
                if section_number not in sections_with_primary[division]:
                    sections_with_primary[division][section_number] = {
                        "multi": [], "single": []}

                if len(full_range) > 1:
                    sections_with_primary[division][section_number]["multi"].append(
                        full_range)
                else:
                    sections_with_primary[division][section_number]["single"].append(
                        full_range[0])
            else:
                sections_with_reference_count += 1

            total_divisions.add(division)
            total_sections.add(section_number)

            result = await db.update_section_pages(
                spec_id=spec_id,
                section_number=section_number,
                primary_pages=full_range if is_primary else [],
                reference_pages=full_range if not is_primary else []
            )
            section_id = result.get('section_id')
            if section_id:
                await db.save_classification_result(
                    section_id=section_id,
                    custom_id=custom_id,
                    result=content
                )
            else:
                logger.error(
                    f"Failed to update section pages for {section_number} - no section_id returned")
                errors += 1

    await db.update_project(
        spec_id=spec_id,
        classification_status="complete",
        total_divisions=len(total_divisions),
        total_sections=len(total_sections),
        sections_with_primary=sections_with_primary_count,
        sections_with_reference=sections_with_reference_count,
        errors=errors
    )

    for section_number in total_sections:
        division = section_number[:2]
        if division not in sections_with_primary or section_number not in sections_with_primary[division]:
            await db.update_section_summary_status(
                spec_id=spec_id,
                section_number=section_number,
                summary_status="manual"
            )


    logger.info(f"failed_custom_ids: {failed_custom_ids}")
    return {
        "failed_custom_ids": list(failed_custom_ids),
        "sections_with_primary": sections_with_primary,
    }


async def build_classification_requests(
    sections: dict[int, dict],
    spec_id: str,
    system_prompt: str,
    dynamic_schema: Callable[[str], Type[BaseModel]],
    s3: S3Bucket,
    s3_client: any,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 1024
) -> list[dict]:
    requests = []

    for division_number, division in sections.items():
        for section_number, section in division.items():
            for multi in section.get("multi", []):
                start_index, end_index = multi[:2]
                last_index = multi[-1]

                safe_section_number = section_number.replace(".", "_")
                custom_id = f'{division_number}-{safe_section_number}-{spec_id}-{start_index}-{last_index}'

                content_blocks: List[dict] = []
                pages_analyzed = []
                async for page in s3.get_converted_pages_generator_with_client(
                    spec_id, s3_client, start_index, end_index + 1
                ):
                    content_blocks.extend(
                        anthropic.page_blocks(page["page_index"], page["text"], page["bytes"], page["media_type"]))
                    pages_analyzed.append(page["page_index"])

                request = await anthropic.build_claude_request(
                    custom_id,
                    content_blocks,
                    system_prompt=anthropic.build_prompt(system_prompt, {
                                                         "section_number": section_number, "pages_analyzed": pages_analyzed}),
                    schema=dynamic_schema(section_number),
                    model=model,
                    max_tokens=max_tokens
                )
                requests.append(request)

            for single in section.get("single", []):
                safe_section_number = section_number.replace(".", "_")
                custom_id = f'{division_number}-{safe_section_number}-{spec_id}-{single}'

                content_blocks: List[dict] = []
                pages_analyzed = []
                async for page in s3.get_converted_pages_generator_with_client(
                    spec_id, s3_client, single, single + 1
                ):
                    content_blocks.extend(
                        anthropic.page_blocks(page["page_index"], page["text"], page["bytes"], page["media_type"]))
                    pages_analyzed.append(page["page_index"])

                request = await anthropic.build_claude_request(
                    custom_id,
                    content_blocks,
                    system_prompt=anthropic.build_prompt(system_prompt, {
                                                         "section_number": section_number, "pages_analyzed": pages_analyzed}),
                    schema=dynamic_schema(section_number),
                    model=model,
                    max_tokens=max_tokens
                )

                requests.append(request)

    return requests


def structure_failed_custom_ids(failed_custom_ids: list[str]):
    """Structure failed custom ids for background task"""
    divisions_and_sections = {}

    for failed_custom_id in failed_custom_ids:
        split_custom_id = failed_custom_id.split('-')

        division_number = split_custom_id[0]
        section_number = split_custom_id[1].replace("_", ".")

        custom_id_length = len(split_custom_id)

        # If there are multiple pages analyzed, use the start and end index of the last page
        start_index = split_custom_id[-2] if custom_id_length == 9 else split_custom_id[-1]
        end_index = split_custom_id[-1]

        if division_number not in divisions_and_sections:
            divisions_and_sections[division_number] = {}

        if section_number not in divisions_and_sections[division_number]:
            divisions_and_sections[division_number][section_number] = {
                "multi": [], "single": []}

        if custom_id_length == 9:
            divisions_and_sections[division_number][section_number]['multi'].append(
                [page for page in range(int(start_index), int(end_index) + 1)])
        else:
            divisions_and_sections[division_number][section_number]['single'].append(
                int(start_index))

    return divisions_and_sections


async def page_classification(spec_id: str, divisions_and_sections: dict[str, dict[str, List[int]]], retry: int = 0, max_retries: int = 3):
    """Background task to classify all sections"""
    s3 = S3Bucket()
    start_time = time.time()

    try:
        logger.info(f"Starting background classification for {spec_id}")

        batch_ids = []
        batch_results = []

        async with s3.s3_client() as s3_client:
            requests = await build_classification_requests(
                sections=divisions_and_sections,
                spec_id=spec_id,
                system_prompt=CLASSIFICATION_PROMPT,
                dynamic_schema=make_classification_schema,
                s3=s3,
                s3_client=s3_client,
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024
            )

        batches = anthropic.split_batch(requests)
        for batch in batches:
            result = await anthropic.create_batch(batch)
            batch_ids.append(result["batch_id"])

        poll_results = await asyncio.gather(*[anthropic.poll_and_fetch_batch_results(batch_id) for batch_id in batch_ids])
        batch_results.extend(poll_results)

        results = await save_classification_results(spec_id, batch_results)
        failed_custom_ids = results.get("failed_custom_ids", set())

        asyncio.create_task(
            section_summaries(
                spec_id,
                results.get("sections_with_primary", {}),
                retry,
                max_retries
            )
        )

        if failed_custom_ids and retry < max_retries:
            logger.info(
                f"Failed custom ids found: {failed_custom_ids}, retrying...")
            structured_failed_custom_ids = structure_failed_custom_ids(
                failed_custom_ids)
            asyncio.create_task(
                page_classification(
                    spec_id,
                    structured_failed_custom_ids,
                    retry + 1,
                    max_retries
                )
            )
        else:
            completion_time = format_time(time.time() - start_time)
            send_mail(spec_id, completion_time)
            logger.info(f"Classification complete for {spec_id}")

    except Exception as e:
        logger.error(f"Classification failed for {spec_id}: {e}")
        return {"error": f"Classification failed for {spec_id}: {e}"}, 500
