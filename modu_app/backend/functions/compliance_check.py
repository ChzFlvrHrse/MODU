import logging
import json
import asyncio
from typing import Optional, List
from classes import db, S3Bucket, Anthropic, make_spec_check_schema, make_compare_compliance_runs_schema
from classes.base_models import RequirementFinding
from prompts import SPEC_CHECK_PROMPT, SPEC_CHECK_DRAWINGS_PROMPT, COMPARE_COMPLIANCE_RUNS_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = S3Bucket()
anthropic = Anthropic()


async def compliance_check(
    package_id: int,
    spec_id: str,
    section_id: int,
    section_number: str,
    submittals: list[dict],
    submittal_ids: Optional[List[int]],
) -> dict:
    try:

        # Check if the submittals are only shop drawings
        type_ids = [submittal.get("submittal_type_id")
                    for submittal in submittals]
        is_drawing_only = set(type_ids) == {1042}

        max_tokens = 25000
        effort = "high"
        if is_drawing_only:
            logger.info("Submittals are only shop drawings")
            system_prompt = anthropic.build_prompt(
                SPEC_CHECK_DRAWINGS_PROMPT, {"section_number": section_number})
            # max_tokens = 16000
            # effort = "medium"
        else:
            logger.info("Submittals are not only shop drawings")
            system_prompt = anthropic.build_prompt(
                SPEC_CHECK_PROMPT, {"section_number": section_number})
            # max_tokens = 25000
            # effort = "high"

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
            schema=make_spec_check_schema(section_number),
            max_tokens=max_tokens,
            adaptive_thinking=is_drawing_only,
            effort=effort,
            cache_system_prompt=True
        )

        if claude_request.get("status") == "success":
            logger.info(
                f"Claude request succeeded for package_id={package_id}, section_number={section_number}")

            # def compute_compliance_score(
            #     findings: list[dict],
            #     non_conformances: list[dict],
            #     missing_items: list[dict],
            #     total_requirements: int = None,
            # ) -> float:

            # # NOTE: Weights are subject to change.
            #     WEIGHTS = {
            #         "critical": 0.75,
            #         "major": 0.4,
            #         "minor": 0.1,
            #         "clarification_needed": 0.1,
            #         "missing_required": 0.15,
            #         "missing_optional": 0.05,
            #     }

            #     if total_requirements is None:
            #         total_requirements = len([
            #             f for f in findings if f["status"] != "not_applicable"
            #         ])
            #     if total_requirements == 0:
            #         return 0.0

            #     penalty = 0.0

            #     for nc in non_conformances:
            #         severity = nc.get("severity", "minor")
            #         penalty += WEIGHTS.get(severity, 0.1)

            #     for item in missing_items:
            #         if item.get("required", True):
            #             penalty += WEIGHTS["missing_required"]
            #         else:
            #             penalty += WEIGHTS["missing_optional"]

            #     for f in findings:
            #         if f["status"] == "clarification_needed":
            #             penalty += WEIGHTS["clarification_needed"]

            #     raw = 1.0 - (penalty / total_requirements)
            #     return round(max(0.0, raw), 2)

            # def compute_is_compliant(findings: list[dict], non_conformances: list[dict], missing_items: list[dict], threshold: float = 0.85) -> bool:
            #     score = compute_compliance_score(findings, non_conformances, missing_items)
            #     has_critical_or_major = any(
            #         nc["severity"] in ("critical", "major")
            #         for nc in non_conformances
            #     )
            #     return score > threshold and not has_critical_or_major

            # response = claude_request.get("response")
            # findings = response.get("requirement_findings", [])
            # non_conformances = response.get("non_conformances", [])
            # missing_items = response.get("missing_items", [])

            # section_summary = await db.get_section_summary(section_id)
            # key_requirements = json.loads(section_summary.get("key_requirements", []))
            # total_requirements = len(key_requirements)

            # response["compliance_score"] = compute_compliance_score(
            #     findings,
            #     non_conformances,
            #     missing_items,
            #     total_requirements=total_requirements
            # )
            # response["is_compliant"] = compute_is_compliant(
            #     findings,
            #     non_conformances,
            #     missing_items
            # )

            return {
                "status": "success",
                "result": claude_request.get("response"),
                "pipeline": "drawings" if is_drawing_only else "general",
                "submittal_ids": [s.get("id") for s in submittals],
                "input_tokens": claude_request.get("input_tokens"),
                "output_tokens": claude_request.get("output_tokens"),
                "total_tokens": claude_request.get("total_tokens"),
            }
        else:
            logger.error(
                f"Claude request failed: {claude_request.get('error')}")
            return {
                "status": "error",
                "error": claude_request.get("error")
            }
    except Exception as e:
        logger.error(f"Error in compliance_check: {e}")
        return {"status": "error", "error": str(e)}


# async def stream_compliance_check(
#     package_id: int,
#     spec_id: str,
#     section_id: int,
#     section_number: str,
#     submittals: list[dict],
#     submittal_ids: Optional[List[int]],
# ):
#     queue = asyncio.Queue()

#     async def on_delta(text: str):
#         await queue.put({"type": "delta", "text": text})

#     async def run_check():
#         result = await compliance_check(
#             package_id=package_id,
#             spec_id=spec_id,
#             section_id=section_id,
#             section_number=section_number,
#             submittals=submittals,
#             submittal_ids=submittal_ids,
#             on_delta=on_delta,
#         )
#         await queue.put({"type": "done", "result": result})

#     task = asyncio.create_task(run_check())

#     while True:
#         try:
#             item = await asyncio.wait_for(queue.get(), timeout=5)
#         except asyncio.TimeoutError:
#             logger.info("Stream timeout, sending keepalive")
#             yield ": keepalive\n\n"
#             continue
#         except Exception as e:
#             logger.error(f"Error in stream_compliance_check: {e}")
#             yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
#             break

#         if item["type"] == "delta":
#             yield f"data: {json.dumps(item)}\n\n"
#         elif item["type"] == "done":
#             result = item["result"]
#             if result.get("status") == "success":
#                 prev_runs = await db.get_compliance_runs(
#                     package_id,
#                     submittal_id=submittal_ids[0] if submittal_ids else None
#                 )
#                 if prev_runs:
#                     latest = prev_runs[0]
#                     await db.update_compliance_run(
#                         compliance_run_id=latest.get("id"),
#                         submittal_ids=result.get("submittal_ids"),
#                         compliance_result=result.get("result"),
#                         compliance_score=result.get(
#                             "result").get("compliance_score"),
#                         is_compliant=result.get("result").get("is_compliant"),
#                         pipeline=result.get("pipeline"),
#                         prompt_version=latest.get("prompt_version") + 1,
#                         token_count=result.get("total_tokens"),
#                     )
#                 else:
#                     await db.create_compliance_run(
#                         package_id=package_id,
#                         spec_id=spec_id,
#                         section_id=section_id,
#                         submittal_ids=result.get("submittal_ids"),
#                         compliance_result=result.get("result"),
#                         compliance_score=result.get(
#                             "result").get("compliance_score"),
#                         is_compliant=result.get("result").get("is_compliant"),
#                         pipeline=result.get("pipeline"),
#                         model="claude-sonnet-4-6",
#                         token_count=result.get("total_tokens"),
#                     )
#                 await db.update_package_after_run(
#                     package_id=package_id,
#                     compliance_result=result.get("result"),
#                     compliance_score=result.get(
#                         "result").get("compliance_score"),
#                     checked_submittal_ids=result.get("submittal_ids"),
#                 )
#                 yield f"data: {json.dumps({'type': 'done', 'result': result})}\n\n"
#             else:
#                 yield f"data: {json.dumps({'type': 'error', 'error': result.get('error')})}\n\n"
#             break

async def compare_compliance_runs(
    package_id_1: int,
    package_id_2: int,
    section_number: str,
):
    try:
        package_1 = await db.get_submittal_package(package_id_1)
        package_2 = await db.get_submittal_package(package_id_2)

        compliance_result_1 = package_1.get("compliance_result")
        compliance_result_2 = package_2.get("compliance_result")

        if not compliance_result_1 or not compliance_result_2:
            return {"status": "error", "error": "One or both packages missing compliance_result"}

        # compliance_result is stored as a JSON string in the DB
        if isinstance(compliance_result_1, str):
            compliance_result_1 = json.loads(compliance_result_1)
        if isinstance(compliance_result_2, str):
            compliance_result_2 = json.loads(compliance_result_2)

        system_prompt = anthropic.build_prompt(
            COMPARE_COMPLIANCE_RUNS_PROMPT, {"section_number": section_number}
        )

        content_blocks = [
            {
                "type": "text",
                "text": (
                    f"Compare the following two compliance runs for spec section {section_number}.\n\n"
                    f"PACKAGE A (id={package_id_1}, name={package_1.get('package_name', 'Unknown')}):\n"
                    f"{json.dumps(compliance_result_1, indent=2)}"
                )
            },
            {
                "type": "text",
                "text": (
                    f"PACKAGE B (id={package_id_2}, name={package_2.get('package_name', 'Unknown')}):\n"
                    f"{json.dumps(compliance_result_2, indent=2)}"
                )
            },
        ]

        token_count = await anthropic.count_tokens_content_blocks(content_blocks, system_prompt)
        logger.info(f"Token count: {token_count}")

        claude_request = await anthropic.claude(
            content_blocks=content_blocks,
            system_prompt=system_prompt,
            schema=make_compare_compliance_runs_schema(section_number),
            max_tokens=16000,
            effort="medium",
            cache_system_prompt=True
        )

        if claude_request.get("status") == "success":
            logger.info(
                f"Comparison succeeded: package_id_1={package_id_1}, "
                f"package_id_2={package_id_2}, section={section_number}"
            )
            return {
                "status": "success",
                "result": claude_request.get("response"),
                "package_a_name": package_1.get("package_name"),
                "package_b_name": package_2.get("package_name"),
                "input_tokens": claude_request.get("input_tokens"),
                "output_tokens": claude_request.get("output_tokens"),
                "total_tokens": claude_request.get("total_tokens"),
            }
        else:
            logger.error(
                f"Claude request failed: {claude_request.get('error')}")
            return {"status": "error", "error": claude_request.get("error")}

    except Exception as e:
        logger.error(f"Error in compare_compliance_runs: {e}")
        return {"status": "error", "error": str(e)}
