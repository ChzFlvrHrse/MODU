from typing import Any, Dict
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Callable, Type, List
from prompts import SUMMARY_PROMPT
import logging
import asyncio
import time
import os
import resend
from classes import (
    S3Bucket,
    Anthropic,
    db,
    make_summary_schema,
    PDFPageConverter
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic = Anthropic()
pdf_converter = PDFPageConverter()


def send_mail(spec_id: str, completion_time: float) -> Dict:
    resend.api_key = os.getenv("RESEND_API_KEY")
    params: resend.Emails.SendParams = {
        # This is Resend's built-in test sender
        "from": "MODU <onboarding@resend.dev>",
        "to": ["nscott1010@gmail.com"],
        "subject": "MODU Summary Complete",
        # Should be dynamic for second, minute, hour, etc.
        "html": f"<strong>The MODU summary process has completed successfully for {spec_id} in {completion_time}.</strong>",
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


async def save_summary_results(spec_id: str, batch_results: list[list[dict]]) -> dict[str, Any]:
    total_summaries = 0
    errors = 0
    failed_custom_ids = set()
    sections: dict[str, dict] = {}

    for batch in batch_results:
        for item in batch:
            custom_id = item.get('custom_id', '')

            if item.get('type') == 'errored':
                logger.error(f"Errored for {custom_id}: {item.get('error')}")
                errors += 1
                failed_custom_ids.add(custom_id)
                continue

            split_custom_id = custom_id.split('-')
            content = item.get('content')
            section_number = split_custom_id[1].replace("_", ".")

            custom_id_length = len(split_custom_id)
            start_index = split_custom_id[-2] if custom_id_length == 9 else split_custom_id[-1]
            end_index = split_custom_id[-1]
            pages_summarized = list(
                range(int(start_index), int(end_index) + 1))

            if section_number not in sections:
                sections[section_number] = {
                    **content,
                    "pages_summarized": pages_summarized,
                    "pages_not_summarized": []
                }
            else:
                # merge list fields
                for field in ['key_requirements', 'materials', 'submittals', 'testing', 'related_sections']:
                    sections[section_number][field] = sections[section_number].get(
                        field, []) + content.get(field, [])
                sections[section_number]['pages_summarized'] += pages_summarized

    # now save each consolidated section
    for section_number, summary in sections.items():
        section = await db.get_section(spec_id, section_number)
        section_id = section.get('id') if section else None

        if section_id:
            await db.save_section_summary(spec_id, {
                **summary,
                "section_id": section_id,
                "section_number": section_number,
            })
            await db.update_section_title(section_id, summary.get('section_title', 'Undocumented Section Number (MSF2020)'))
            await db.update_section_summary_status(spec_id, section_number)
            total_summaries += 1
        else:
            logger.error(f"Section not found for {section_number}")
            errors += 1

    logger.info(f"failed_custom_ids: {failed_custom_ids}")
    return {
        "failed_custom_ids": list(failed_custom_ids),
        "total_summaries": total_summaries,
        "errors": errors
    }


async def build_summary_requests(
    sections: dict[int, dict],
    spec_id: str,
    system_prompt: str,
    dynamic_schema: Callable[[str], Type[BaseModel]],
    s3: S3Bucket,
    s3_client: any,
    model: str = "claude-sonnet-4-5-20250929",
    max_tokens: int = 8192
) -> list[dict]:
    requests = []

    for division_number, division in sections.items():
        for section_number, section in division.items():
            for multi in section.get("multi", []):
                start_index, end_index = multi[0], multi[-1]
                page_indices = list[int](range(start_index, end_index + 1))

                safe_section_number = section_number.replace(".", "_")
                custom_id = f'{division_number}-{safe_section_number}-{spec_id}-{start_index}-{end_index}'

                content_blocks = []
                for page in page_indices:
                    key = f"{spec_id}/original_pages/page_{page:04d}.pdf"
                    url = await s3.generate_presigned_url(key, s3_client)
                    content_blocks.append(anthropic.pdf_document_block(url))

                request = await anthropic.build_claude_request(
                    custom_id,
                    content_blocks,
                    system_prompt=anthropic.build_prompt(system_prompt, {
                        "section_number": section_number, "pages_analyzed": page_indices}),
                    schema=dynamic_schema(section_number),
                    model=model,
                    max_tokens=max_tokens
                )
                requests.append(request)

            for single in section.get("single", []):
                safe_section_number = section_number.replace(".", "_")
                custom_id = f'{division_number}-{safe_section_number}-{spec_id}-{single}'

                key = f"{spec_id}/original_pages/page_{single:04d}.pdf"
                url = await s3.generate_presigned_url(key, s3_client)
                content_blocks = [anthropic.pdf_document_block(url)]

                request = await anthropic.build_claude_request(
                    custom_id,
                    content_blocks,
                    system_prompt=anthropic.build_prompt(
                        system_prompt, {"section_number": section_number, "pages_analyzed": [single]}),
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


async def section_summaries(spec_id: str, sections_with_summaries: dict[str, dict[str, List[int]]], retry: int = 0, max_retries: int = 3):
    """Background task to classify all sections"""
    s3 = S3Bucket()
    start_time = time.time()

    try:
        logger.info(f"Starting background summary for {spec_id}")

        batch_ids = []
        batch_results = []

        async with s3.s3_client() as s3_client:
            requests = await build_summary_requests(
                sections=sections_with_summaries,
                spec_id=spec_id,
                system_prompt=SUMMARY_PROMPT,
                dynamic_schema=make_summary_schema,
                s3=s3,
                s3_client=s3_client,
                model="claude-sonnet-4-5-20250929",
                max_tokens=8192
            )

        batches = anthropic.split_batch(requests)
        for batch in batches:
            result = await anthropic.create_batch(batch)
            batch_ids.append(result["batch_id"])

        poll_results = await asyncio.gather(*[anthropic.poll_and_fetch_batch_results(batch_id) for batch_id in batch_ids])
        batch_results.extend(poll_results)

        results = await save_summary_results(spec_id, batch_results)
        failed_custom_ids = results.get("failed_custom_ids", set())

        if failed_custom_ids and retry < max_retries:
            logger.info(
                f"Failed custom ids found: {failed_custom_ids}, retrying...")
            structured_failed_custom_ids = structure_failed_custom_ids(
                failed_custom_ids)
            asyncio.create_task(
                section_summaries(
                    spec_id,
                    structured_failed_custom_ids,
                    retry + 1,
                    max_retries
                )
            )
        else:
            await db.update_project(spec_id, summary_status="complete")
            completion_time = format_time(time.time() - start_time)
            send_mail(spec_id, completion_time)
            logger.info(f"Summary complete for {spec_id} in {completion_time}")

    except Exception as e:
        logger.error(f"Summary failed for {spec_id}: {e} in {format_time(time.time() - start_time)}")
        return {"error": f"Summary failed for {spec_id}: {e}"}, 500
