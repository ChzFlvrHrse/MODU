from typing import Dict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import logging, asyncio, time, os, resend
from classes import S3Bucket, Anthropic, db
from typing import Callable, Type, List, Tuple, Optional

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic = Anthropic()

PagePayload = Tuple[int, str, Optional[bytes], Optional[str]]

def make_classification_schema(section_number: str) -> type[BaseModel]:
    class PageClassification(BaseModel):
        reasoning: str = Field(
            description="Brief explanation of the classification decision"
        )
        pages_analyzed: list[int] = Field(
            description="List of page numbers that were analyzed"
        )
        confidence: float = Field(
            description="Confidence level in the classification between 0 and 1"
        )
        is_primary: bool = Field(
            description=f"True ONLY if the page contains the primary specification body for section {section_number} specifically. Must be false if reasoning concludes content belongs to a different section."
        )
    return PageClassification


CLASSIFICATION_PROMPT = """
You are classifying construction specification pages.

Determine if these pages contain the PRIMARY specification body for the given section number, or if they are just references/context.

PRIMARY specification content has:
- Section title header (e.g., "SECTION {section_number}")
- CSI structure: "PART 1 - GENERAL", "PART 2 - PRODUCTS", "PART 3 - EXECUTION"
- Dense technical requirements, materials, installation procedures
- Numbered subsections (1.1, 1.2, 2.1, etc.)
- Submittal requirements, quality standards, testing procedures
- Forms, templates, or worksheets that ARE the section deliverable (e.g., submittal forms, request forms, checklists)
- Administrative procedures or requirements that constitute the section content
- Any substantive content that defines what this section requires

NOT primary content:
- Table of contents pages - even if they list this section number, a TOC is NEVER primary content
- Single-line references ("See Section {section_number}")
- Substitution/product lists
- Cross-references from other sections
- Divider pages with minimal content
- Pages whose primary content belongs to a different section number than the one being analyzed

Section number being analyzed: {section_number}. Only classify as primary if this page contains specification content FOR section {section_number} specifically. Pages provided: {pages_analyzed}.

IMPORTANT: Your JSON output must match your reasoning. If your reasoning concludes the page is NOT primary for the section being analyzed, is_primary MUST be false. If you identify the page belongs to a different section number, is_primary MUST be false regardless of how dense or technical the content is.

Note: You may only see the first 2-3 pages of a longer section. If those pages show clear PRIMARY indicators, classify as primary.
"""


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


async def save_batch_results(spec_id: str, batch_results: list[list[dict]]):
    total_sections = set()
    total_divisions = set()
    sections_with_primary = 0
    sections_reference_only = 0
    errors = 0

    for batch in batch_results:
        for item in batch:
            custom_id = item.get('custom_id', '')

            content = item.get('content')
            if not content:
                logger.error(f"Missing content for {custom_id}")
                errors += 1
                continue

            split_custom_id = custom_id.split('-')

            division = split_custom_id[0]
            section_number = split_custom_id[1].replace("_", ".")
            is_primary = content.get('is_primary', False)
            pages_analyzed = content.get('pages_analyzed', [])

            start_index = split_custom_id[-2] if len(
                pages_analyzed) > 1 else split_custom_id[-1]
            end_index = split_custom_id[-1]

            full_range = [page for page in range(
                int(start_index), int(end_index) + 1)]

            if is_primary:
                sections_with_primary += 1
            else:
                sections_reference_only += 1

            total_divisions.add(division)
            total_sections.add(section_number)

            section_data = {
                "section_number": section_number,
                "status": "complete",
                "primary_pages": full_range if is_primary else [],
                "reference_pages": full_range if not is_primary else []
            }

            logger.info(f"Section data: {section_data}")

            result = await db.update_section_pages(spec_id, section_data)
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
        status="complete",
        total_divisions=len(total_divisions),
        total_sections=len(total_sections),
        sections_with_primary=sections_with_primary,
        sections_reference_only=sections_reference_only,
        errors=errors
    )

    logger.info(f"Classification complete for {spec_id}")
    return batch_results


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

                page_payloads: List[PagePayload] = []
                pages_analyzed = []
                async for page in s3.get_converted_pages_generator_with_client(
                    spec_id, s3_client, start_index, end_index + 1
                ):
                    page_payloads.append(
                        (page["page_index"], page["text"], page["bytes"], page["media_type"]))
                    pages_analyzed.append(page["page_index"])

                request = await anthropic.build_claude_request(
                    custom_id,
                    page_payloads,
                    system_prompt=anthropic.build_prompt(system_prompt, {"section_number": section_number, "pages_analyzed": pages_analyzed}),
                    schema=dynamic_schema(section_number),
                    model=model,
                    max_tokens=max_tokens
                )
                if request is not None:
                    requests.append(request)

            for single in section.get("single", []):
                safe_section_number = section_number.replace(".", "_")
                custom_id = f'{division_number}-{safe_section_number}-{spec_id}-{single}'

                page_payloads: List[PagePayload] = []
                pages_analyzed = []
                async for page in s3.get_converted_pages_generator_with_client(
                    spec_id, s3_client, single, single + 1
                ):
                    page_payloads.append(
                        (page["page_index"], page["text"], page["bytes"], page["media_type"]))
                    pages_analyzed.append(page["page_index"])

                request = await anthropic.build_claude_request(
                    custom_id,
                    page_payloads,
                    system_prompt=anthropic.build_prompt(system_prompt, {"section_number": section_number, "pages_analyzed": pages_analyzed}),
                    schema=dynamic_schema(section_number),
                    model=model,
                    max_tokens=max_tokens
                )
                if request is not None:
                    requests.append(request)

    return requests


async def run_classification_background(spec_id: str, divisions_and_sections: dict):
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

        await save_batch_results(spec_id, batch_results)

    except Exception as e:
        logger.error(f"Classification failed for {spec_id}: {e}")
        return {"error": f"Classification failed for {spec_id}: {e}"}, 500
    finally:
        completion_time = format_time(time.time() - start_time)
        send_mail(spec_id, completion_time)
        logger.info(f"Classification complete for {spec_id}")
