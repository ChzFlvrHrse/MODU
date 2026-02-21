from classes.s3_buckets import S3Bucket
from anthropic import AsyncAnthropic, RateLimitError
from dotenv import load_dotenv
import os
import logging
import asyncio
from pydantic import BaseModel, Field
from classes import db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class PageClassification(BaseModel):
    is_primary: bool = Field(
        description="Whether these pages contain the primary specification body for this section"
    )
    confidence: float = Field(
        description="Confidence level in the classification between 0 and 1"
    )
    reasoning: str = Field(
        description="Brief explanation of the classification decision"
    )
    pages_analyzed: list[int] = Field(
        description="List of page numbers that were analyzed"
    )


async def classify_block_ai(
    pages_to_analyze: list[int],
    section_number: str,
    spec_id: str,
    s3: S3Bucket,
    s3_client: any
) -> dict:
    system_prompt = """You are classifying construction specification pages.

Determine if these pages contain the PRIMARY specification body for the given section number, or if they are just references/context.

PRIMARY specification content has:
- Section title header (e.g., "SECTION 03 30 00 - CAST-IN-PLACE CONCRETE")
- CSI structure: "PART 1 - GENERAL", "PART 2 - PRODUCTS", "PART 3 - EXECUTION"
- Dense technical requirements, materials, installation procedures
- Numbered subsections (1.1, 1.2, 2.1, etc.)
- Submittal requirements, quality standards, testing procedures
- Forms, templates, or worksheets that ARE the section deliverable (e.g., submittal forms, request forms, checklists)
- Administrative procedures or requirements that constitute the section content
- Any substantive content that defines what this section requires

NOT primary content:
- Table of contents pages - even if they list this section number, a TOC is NEVER primary content
- Single-line references ("See Section 03 30 00")
- Substitution/product lists
- Cross-references from other sections
- Divider pages with minimal content

Note: You may only see the first 2-3 pages of a longer section. If those pages show clear PRIMARY indicators, classify as primary."""

    # Fetch pages using generator
    start_index = min(pages_to_analyze)
    end_index = max(pages_to_analyze) + 1

    pages_dict = {}
    async for page in s3.get_converted_pages_generator_with_client(
        spec_id, s3_client, start_index, end_index
    ):
        if page["page_index"] in pages_to_analyze:
            pages_dict[page["page_index"]] = page

    # Build content blocks
    content = []
    for page_num in sorted(pages_to_analyze):
        page = pages_dict.get(page_num)

        if not page:
            logger.warning(f"Page {page_num} not found in pages_dict")
            continue

        text = page.get("text", "")
        image_bytes = page.get("bytes")

        if text:
            content.append({
                "type": "text",
                "text": f"===== PAGE {page_num} TEXT =====\n{text}\n"
            })

        if image_bytes:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_bytes
                }
            })

    if not content:
        logger.warning(f"No content found for section {section_number}")
        return {
            "is_primary": False,
            "confidence": 0.0,
            "reasoning": "No content found for section",
            "pages_analyzed": pages_to_analyze
        }

    content.append({
        "type": "text",
        "text": f"Section number being analyzed: {section_number}"
    })

    try:
        # Call Claude & utilize prompt caching to avoid duplicate calls
        res = await client.beta.messages.parse(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            betas=["structured-outputs-2025-11-13",
                   "prompt-caching-2024-07-31"],
            output_format=PageClassification,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {
                    "type": "ephemeral"
                }
            }],
            messages=[{"role": "user", "content": content}]
        )

        parsed = res.parsed_output
        if parsed:
            result = parsed.model_dump()
            logger.info(f"Classification result type: {type(result)}")
            logger.info(f"Classification result: {result}")
            for key, value in result.items():
                logger.info(f"{key}: {type(value)}")
            return result
        else:
            return {
                "is_primary": False,
                "confidence": 0.0,
                "reasoning": "No classification was made",
                "pages_analyzed": pages_to_analyze
            }
    except Exception as e:
        logger.error(f"Error classifying block: {e}")
        return {
            "is_primary": False,
            "confidence": 0.0,
            "reasoning": "No classification was made",
            "pages_analyzed": pages_to_analyze
        }


# Classifies pages for a section as primary, referential, or other
async def classify_section(
    section_number: str,
    section_data: dict,
    spec_id: str,
    s3: S3Bucket,
    s3_client: any
) -> list[dict]:
    results = []

    # Classify each contiguous block (first 2 pages only)
    for block in section_data["multi"]:
        if not block:
            continue

        pages_to_analyze = block[:2]  # Get the first 2 pages of the block
        result = await classify_block_ai(
            pages_to_analyze=pages_to_analyze,
            section_number=section_number,
            spec_id=spec_id,
            s3=s3,
            s3_client=s3_client
        )
        result["block_type"] = "contiguous"
        result["full_block"] = block  # Store full block for later use
        results.append(result)

    # Classify each isolated page
    for page in section_data["single"]:
        result = await classify_block_ai(
            pages_to_analyze=[page],
            section_number=section_number,
            spec_id=spec_id,
            s3=s3,
            s3_client=s3_client
        )
        result["block_type"] = "isolated"
        results.append(result)

    return results


async def update_section_pages(spec_id: str, division: str, section_results: dict):
    """Save section results to database"""
    update_count = 0
    error_count = 0

    for section_num, section_info in section_results.items():
        try:
            # Check if this section had a classification error
            if section_info.get("error"):
                logger.warning(
                    f"Section {section_num} had classification error: {section_info['error']}")
                status = "failed"
                primary_pages = []
                reference_pages = []
                classification_results = []
                error_count += 1
            else:
                status = "complete"
                primary_pages = section_info.get("primary_pages", [])
                reference_pages = section_info.get("reference_pages", [])
                classification_results = section_info.get(
                    "classification_results", [])

            logger.info(f"Updating section {section_num} for {spec_id}")
            section_id = await db.update_section_pages(
                spec_id=spec_id,
                division=division,
                section_number=section_num,
                section_name=section_info["section_name"],
                status=status,
                primary_pages=primary_pages,
                reference_pages=reference_pages
            )

            if section_id:
                for result in classification_results:
                    try:
                        await db.save_classification_result(
                            section_id=section_id,
                            result=result
                        )
                    except Exception as e:
                        logger.error(
                            f"Error saving classification result for section {section_num}: {e}")
                        error_count += 1
                update_count += 1
            else:
                logger.error(
                    f"Failed to update section {section_num} - no section_id returned")
                error_count += 1

        except Exception as e:
            logger.error(f"Error updating section {section_num}: {e}")
            error_count += 1

    logger.info(f"Updated {update_count} sections, {error_count} errors")
    return update_count, error_count

# Classifies all sections for a specification into primary, referential, or other
# Each division is ran one at a time. i.e. run through division 01 first and wait for it to complete before running division 02.


async def classify_all_sections_by_division(
    spec_id: str,
    divisions_and_sections: dict,
    s3: S3Bucket,
    s3_client: any,
    batch_size: int = 5,  # Process this many sections at a time
    delay_between_calls: float = 5.0,
    delay_between_divisions: float = 10.0,
    rate_limit_pause: float = 5.0
) -> dict:

    all_results = {}
    divisions = list(divisions_and_sections.keys())

    logger.info(f"Total divisions to process: {len(divisions)}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Delay between calls: {delay_between_calls}s")
    logger.info(f"Delay between divisions: {delay_between_divisions}s\n")

    async def classify_with_delay(section_num, section_info):
        """Classify a section with delay"""
        try:
            await asyncio.sleep(delay_between_calls)

            result = await classify_section(
                section_number=section_num,
                section_data=section_info,
                spec_id=spec_id,
                s3=s3,
                s3_client=s3_client
            )
            return section_num, section_info, result, None

        except RateLimitError as e:
            return section_num, section_info, None, ("RATE_LIMIT", str(e))
        except Exception as e:
            return section_num, section_info, None, ("ERROR", str(e))

    # Process each division sequentially
    for div_idx, division in enumerate(divisions, 1):
        div_sections = divisions_and_sections[division]

        logger.info(f"\n{'='*60}")
        logger.info(f"Division {div_idx}/{len(divisions)}: {division}")
        logger.info(f"{'='*60}")
        logger.info(f"Sections in this division: {len(div_sections)}")

        all_results[division] = {}

        # Convert to list for batching
        sections_list = list(div_sections.items())

        # Process in batches
        for batch_start in range(0, len(sections_list), batch_size):
            batch = sections_list[batch_start:batch_start + batch_size]

            batch_num = batch_start // batch_size + 1
            total_batches = (len(sections_list) + batch_size - 1) // batch_size
            logger.info(
                f"\n  Batch {batch_num}/{total_batches} ({len(batch)} sections)")

            # Create tasks for ONLY this batch
            tasks = [
                classify_with_delay(section_num, section_info)
                for section_num, section_info in batch
            ]

            # Process this batch
            batch_results = await asyncio.gather(*tasks)

            # Track rate limited sections
            rate_limited_sections = []

            # Process batch results
            for section_num, section_info, classification_results, error in batch_results:
                if error:
                    if isinstance(error, tuple) and error[0] == "RATE_LIMIT":
                        rate_limited_sections.append(
                            (section_num, section_info))
                        logger.warning(f"    ⚠ {section_num}: Rate limited")
                    else:
                        error_msg = error[1] if isinstance(
                            error, tuple) else error
                        logger.error(f"    ✗ {section_num}: {error_msg}")
                        all_results[division][section_num] = {
                            "section_name": section_info["title"],
                            "error": error_msg
                        }
                    continue

                # Extract primary/reference pages
                primary_pages = []
                reference_pages = []

                for result in classification_results:
                    if result["is_primary"]:
                        if result["block_type"] == "contiguous":
                            primary_pages.extend(result["full_block"])
                        else:
                            primary_pages.extend(result["pages_analyzed"])
                    else:
                        reference_pages.extend(result["pages_analyzed"])

                all_results[division][section_num] = {
                    "section_name": section_info["title"],
                    "primary_pages": sorted(list(set(primary_pages))),
                    "reference_pages": sorted(list(set(reference_pages))),
                    "classification_results": classification_results
                }

                logger.info(
                    f"    ✓ {section_num}: {len(primary_pages)} primary, {len(reference_pages)} reference")

            # Handle rate limits for this batch
            if rate_limited_sections:
                logger.warning(
                    f"\n  ⚠ Hit rate limits on {len(rate_limited_sections)} sections in batch")
                logger.warning(
                    f"  Pausing for {rate_limit_pause}s then retrying...")
                await asyncio.sleep(rate_limit_pause)

                # Retry rate limited sections
                retry_tasks = [
                    classify_with_delay(section_num, section_info)
                    for section_num, section_info in rate_limited_sections
                ]

                retry_results = await asyncio.gather(*retry_tasks)

                # Process retry results
                for section_num, section_info, classification_results, error in retry_results:
                    if error:
                        error_msg = error[1] if isinstance(
                            error, tuple) else error
                        logger.error(
                            f"    ✗ {section_num} (retry failed): {error_msg}")
                        all_results[division][section_num] = {
                            "section_name": section_info["title"],
                            "error": error_msg
                        }
                        continue

                    # Extract primary/reference pages
                    primary_pages = []
                    reference_pages = []

                    for result in classification_results:
                        if result["is_primary"]:
                            if result["block_type"] == "contiguous":
                                primary_pages.extend(result["full_block"])
                            else:
                                primary_pages.extend(result["pages_analyzed"])
                        else:
                            reference_pages.extend(result["pages_analyzed"])

                    all_results[division][section_num] = {
                        "section_name": section_info["title"],
                        "primary_pages": sorted(list(set(primary_pages))),
                        "reference_pages": sorted(list(set(reference_pages))),
                        "classification_results": classification_results
                    }

                    logger.info(
                        f"✓ {section_num} (retried): {len(primary_pages)} primary, {len(reference_pages)} reference")

        # Save section results to database
        updated, errors = await update_section_pages(spec_id, division, all_results[division])

        if errors > 0:
            logger.info(
                f"Classification incomplete for {spec_id}: {errors} errors")
        else:
            logger.info(f"Classification complete for {spec_id}")

        logger.info(f"\nDivision {division} complete")

        # Delay before next division
        if div_idx < len(divisions):
            logger.info(
                f"Waiting {delay_between_divisions}s before next division...")
            await asyncio.sleep(delay_between_divisions)

    return all_results


async def run_classification_background(spec_id: str, divisions_and_sections: dict):
    """Background task to classify all sections"""
    s3 = S3Bucket()

    try:
        logger.info(f"Starting background classification for {spec_id}")

        async with s3.s3_client() as s3_client:
            results = await classify_all_sections_by_division(
                spec_id=spec_id,
                divisions_and_sections=divisions_and_sections,
                s3=s3,
                s3_client=s3_client
            )

        logger.info(f"Classification complete for {spec_id}")

        total_sections = 0
        sections_with_primary = 0
        sections_reference_only = 0
        errors = 0

        for _, sections in results.items():
            for _, section_info in sections.items():
                if section_info.get("primary_pages"):
                    sections_with_primary += 1
                if section_info.get("reference_pages"):
                    sections_reference_only += 1
                if section_info.get("error"):
                    errors += 1
                total_sections += 1

        await db.update_project(
            spec_id=spec_id,
            status="complete",
            total_divisions=len(divisions_and_sections),
            total_sections=total_sections,
            sections_with_primary=sections_with_primary,
            sections_reference_only=sections_reference_only,
            errors=errors
        )

        logger.info(
            f"Classification complete for {spec_id}")

        return results

    except Exception as e:
        logger.error(f"Classification failed for {spec_id}: {e}")
        return {"error": f"Classification failed for {spec_id}: {e}"}, 500

# async def main():
#     """Run full classification"""

#     spec_id = "a6a02fcb-84e5-41bf-bb56-f44c1a8ef290"
#     s3 = S3Bucket()

#     async with s3.s3_client() as s3_client:
#         logger.info("="*60)
#         logger.info("CLASSIFICATION PROCESS STARTED")
#         logger.info("="*60)
#         logger.info(f"Project ID: {spec_id}\n")

#         results = await classify_all_sections_by_division(
#             spec_id=spec_id,
#             divisions_and_sections=divisions_and_sections,
#             s3=s3,
#             s3_client=s3_client,
#             delay_between_calls=5.0,
#             delay_between_divisions=10.0,
#             rate_limit_pause=10.0
#         )

#         # Save results
#         import json
#         output_file = f"classification_results_{spec_id}.json"
#         with open(output_file, "w") as f:
#             json.dump(results, f, indent=2)

#         logger.info(f"\n{'='*60}")
#         logger.info("CLASSIFICATION COMPLETE")
#         logger.info(f"{'='*60}")
#         logger.info(f"Results saved to: {output_file}\n")

#         # Summary
#         total_sections = sum(len(div) for div in results.values())
#         sections_with_primary = sum(
#             1 for div in results.values()
#             for sec in div.values()
#             if sec.get("primary_pages")
#         )
#         errors = sum(
#             1 for div in results.values()
#             for sec in div.values()
#             if "error" in sec
#         )

#         logger.info("Summary:")
#         logger.info(f"  Total sections: {total_sections}")
#         logger.info(f"  With primary content: {sections_with_primary}")
#         logger.info(
#             f"  References only: {total_sections - sections_with_primary - errors}")
#         logger.info(f"  Errors: {errors}")

# asyncio.run(main())
