import logging
import json
from classes import db, S3Bucket, Anthropic, make_spec_check_schema, make_drawings_spec_check_schema
from prompts import SPEC_CHECK_PROMPT, SPEC_CHECK_DRAWINGS_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = S3Bucket()
anthropic = Anthropic()

async def compliance_check(package_id: int, spec_id: str, section_number: str, submittals: list[dict]):
    try:

        # Check if the submittals are only shop drawings
        type_ids = [submittal.get("submittal_type_id")
                    for submittal in submittals]
        is_drawing_only = set(type_ids) == {1042}

        if is_drawing_only:
            logger.info("Submittals are only shop drawings")
            system_prompt = anthropic.build_prompt(
                SPEC_CHECK_DRAWINGS_PROMPT, {"section_number": section_number})
            max_tokens = 25000
            schema = make_drawings_spec_check_schema(section_number)
            effort = "high"
        else:
            logger.info("Submittals are not only shop drawings")
            system_prompt = anthropic.build_prompt(
                SPEC_CHECK_PROMPT, {"section_number": section_number})
            max_tokens = 16000
            schema = make_spec_check_schema(section_number)
            effort = "medium"

        section = await db.get_section(spec_id, section_number)
        if not section:
            logger.error(
                f"Section not found for spec_id={spec_id}, section_number={section_number}")
            return {"status": "error", "error": "Section not found"}

        primary_pages = json.loads(section.get("primary_pages", "[]"))
        reference_pages = json.loads(section.get("reference_pages", "[]"))
        summary_pages = primary_pages if primary_pages else reference_pages
        summary_page_groups, _ = s3.group_contiguous_pages(summary_pages)

        logger.info(
            f"Fetching {len(summary_pages)} spec page(s) across {len(summary_page_groups)} group(s)")

        # s3_keys = []
        content_blocks = [
            {"type": "text", "text": f"The following are the specification section {section_number} pages:"},
        ]

        # Get original pdf pages
        async with s3.s3_client() as s3_client:
            for group in summary_page_groups:
                for page in group:
                    key = f"{spec_id}/original_pages/page_{page:04d}.pdf"
                    url = await s3.generate_presigned_url(key, s3_client)

                    block = anthropic.pdf_document_block_url(url)
                    content_blocks.append(block)
                    # s3_keys.append(key)

        # logger.info(f"Added {len(s3_keys)} spec page block(s) to content")

        # Add cache control to last block
        content_blocks[-1]["cache_control"] = {"type": "ephemeral"}

        content_blocks.append(
            {"type": "text", "text": "The following are the submittal documents to review:"})

        async with s3.s3_client() as s3_client:
            for submittal in submittals:
                key = submittal.get("s3_key")
                url = await s3.generate_presigned_url(key, s3_client)

                block = anthropic.pdf_document_block_url(url)
                content_blocks.append(block)
                # s3_keys.append(key)

        # logger.info(f"Added {len(submittals)} submittal block(s) to content. Total s3_keys: {len(s3_keys)}")

        # NOTE: Not currently being used, but could be useful for future reference
        # token_count = await anthropic.count_tokens_document(s3_keys, system_prompt)
        # logger.info(f"Token count: {token_count}")

        logger.info("Sending request to Claude")
        claude_request = await anthropic.claude(
            content_blocks=content_blocks,
            system_prompt=system_prompt,
            schema=schema,
            max_tokens=max_tokens,
            adaptive_thinking=is_drawing_only,
            effort=effort,
            cache_system_prompt=True
        )

        if claude_request.get("status") == "success":
            logger.info(
                f"Claude request succeeded for package_id={package_id}, section_number={section_number}")
            return {"status": "success", "result": claude_request.get("response")}
        else:
            logger.error(
                f"Claude request failed: {claude_request.get('error')}")
            return {"status": "error", "error": claude_request.get("error")}
    except Exception as e:
        logger.error(f"Error in compliance_check: {e}")
        return {"status": "error", "error": str(e)}
