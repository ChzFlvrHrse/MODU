import logging
import json
from urllib.parse import unquote
from classes import db, S3Bucket
from prompts import SUMMARY_PROMPT
from quart import Blueprint, jsonify
from classes import Anthropic, make_summary_schema
from csi_masterformat import divisions_and_sections

summary_routes_bp = Blueprint("summary_routes", __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic = Anthropic()


@summary_routes_bp.route("/section_summary/<spec_id>/<section_number>", methods=["GET"])
async def section_summary(spec_id: str, section_number: str):
    try:
        print(spec_id, section_number)
        spec_summary = await db.get_section_summary(spec_id, section_number)
        logger.info(f"Spec summary: {spec_summary}")
        return jsonify({"spec_summary": spec_summary}), 200
    except Exception as e:
        logger.error(f"Error getting spec summary: {e}")
        return jsonify({"error": str(e)}), 500

# NOTE: Consider using 2 prompts for all_contiguous vs not all_contiguous scenarios


@summary_routes_bp.route("/generate_section_summary/<spec_id>/<section_number>", methods=["POST"])
async def generate_section_summary(spec_id: str, section_number: str):
    try:
        s3 = S3Bucket()
        section = await db.get_section(spec_id, section_number)

        if section is None:
            return jsonify({"error": "Section not found"}), 404

        primary_pages = json.loads(section["primary_pages"] or "[]")
        reference_pages = json.loads(section["reference_pages"] or "[]")
        summary_pages = primary_pages if primary_pages else reference_pages

        if not summary_pages:
            return jsonify({"error": "No pages available to summarize"}), 404

        existing_summary = await db.get_section_summary(spec_id, section_number)
        if existing_summary:
            logger.info(f"Existing summary found for {section_number}")
            return jsonify({"existing_summary": existing_summary}), 200

        summary_page_groups, _ = s3.group_contiguous_pages(
            summary_pages)
        resolved_prompt = anthropic.build_prompt(
            SUMMARY_PROMPT, {"section_number": section_number})
        schema = make_summary_schema(section_number)

        content_blocks = []

        async with s3.s3_client() as s3_client:
            for group in summary_page_groups:
                async for page in s3.get_converted_pages_generator_with_client(
                    spec_id, s3_client, group[0], group[-1] + 1
                ):
                    content_blocks.extend(
                        anthropic.page_blocks(page["page_index"], page["text"], page["bytes"], page["media_type"]))

        spec_summary = await anthropic.claude(
            content_blocks,
            system_prompt=resolved_prompt,
            schema=schema,
            max_tokens=8192
        )

        if spec_summary.get("status") == "success":

            summary = spec_summary.get("response")
            section_id = await db.save_section_summary(spec_id, {
                **summary,
                "section_id": section.get("id"),
                "pages_summarized": summary_pages,
                "pages_not_summarized": [],
            })
            if not section_id:
                await db.update_section_summary_status(spec_id, section_number, "manual")
                return jsonify({"error": "Failed to save section summary"}), 500

            if section_number not in divisions_and_sections[section.get("division")]:
                await db.update_section_title(section.get("id"), summary["section_title"])

            await db.update_section_summary_status(spec_id, section_number, "complete")
            return jsonify({"spec_summary": summary}), 200
        else:
            await db.update_section_summary_status(spec_id, section_number, "error")
            return jsonify({"error": spec_summary["error"]}), 400

    except Exception as e:
        await db.update_section_summary_status(spec_id, section_number, "error")
        logger.error(f"Error getting spec summary: {e}")
        return jsonify({"error": str(e)}), 500


@summary_routes_bp.route("/delete/<spec_id>/<section_number>/<summary_id>", methods=["DELETE"])
async def delete_section_summary(spec_id: str, section_number: str, summary_id: int):
    try:
        section_number = unquote(section_number)
        result = await db.delete_section_summary(summary_id)
        if result.get("error"):
            return jsonify({"error": result.get("error")}), 500
        await db.update_section_summary_status(spec_id, section_number, "manual")
        return jsonify({"message": "Section summary deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting section summary: {e}")
        return jsonify({"error": str(e)}), 500

# NOTE: This version utilizes the batch API to generate the summary
# @summary_routes_bp.route("/generate_section_summary/<spec_id>/<section_number>", methods=["POST"])
# async def generate_section_summary(spec_id: str, section_number: str):
#     try:
#         s3 = S3Bucket()
#         section = await db.get_section(spec_id, section_number)

#         if section is None:
#             return jsonify({"error": "Section not found"}), 404

#         primary_pages = json.loads(section["primary_pages"] or "[]")
#         reference_pages = json.loads(section["reference_pages"] or "[]")
#         summary_pages = primary_pages if primary_pages else reference_pages

#         if not summary_pages:
#             return jsonify({"error": "No pages available to summarize"}), 404

#         existing_summary = await db.get_section_summary(spec_id, section_number)
#         if existing_summary:
#             logger.info(f"Existing summary found for {section_number}")
#             return jsonify({"existing_summary": existing_summary}), 200

#         summary_page_groups, all_contiguous = s3.group_contiguous_pages(summary_pages)
#         resolved_prompt = anthropic.build_prompt(SUMMARY_PROMPT, {"section_number": section_number})
#         schema = make_summary_schema(section_number)

#         if all_contiguous:
#             content_blocks = []
#             await db.update_section_summary_status(spec_id, section_number, "pending")

#             async with s3.s3_client() as s3_client:
#                 async for page in s3.get_converted_pages_generator_with_client(
#                     spec_id, s3_client, summary_page_groups[0][0], summary_page_groups[-1][-1] + 1
#                 ):
#                     content_blocks.extend(
#                         anthropic.page_blocks(page["page_index"], page["text"], page["bytes"], page["media_type"]))

#             spec_summary = await anthropic.claude(
#                 content_blocks,
#                 system_prompt=resolved_prompt,
#                 schema=schema,
#                 max_tokens=8192
#             )

#             if spec_summary.get("status") == "success":

#                 summary = spec_summary.get("response")
#                 section_id = await db.save_section_summary(spec_id, {
#                     **summary,
#                     "section_id": section.get("id"),
#                     "pages_summarized": summary_pages,
#                     "pages_not_summarized": [],
#                 })
#                 if not section_id:
#                     await db.update_section_summary_status(spec_id, section_number, "manual")
#                     return jsonify({"error": "Failed to save section summary"}), 500

#                 await db.update_section_summary_status(spec_id, section_number, "complete")
#                 return jsonify({"spec_summary": summary}), 200
#             else:
#                 return jsonify({"error": spec_summary["error"]}), 400

#         else:
#             requests = []
#             await db.update_section_summary_status(spec_id, section_number, "pending")

#             async with s3.s3_client() as s3_client:
#                 for group in summary_page_groups:
#                     content_blocks = []
#                     async for page in s3.get_converted_pages_generator_with_client(
#                         spec_id, s3_client, group[0], group[-1] + 1
#                     ):
#                         content_blocks.extend(
#                             anthropic.page_blocks(page["page_index"], page["text"], page["bytes"], page["media_type"]))

#                     custom_id = f'{section_number}-{section_number[:2]}-{spec_id}-{group[0]}-{group[-1]}'
#                     request = await anthropic.build_claude_request(
#                         custom_id,
#                         content_blocks,
#                         system_prompt=resolved_prompt,
#                         schema=schema,
#                     )
#                     requests.append(request)

#                 if len(requests) == 0:
#                     await db.update_section_summary_status(spec_id, section_number, "error")
#                     return jsonify({"error": "Failed to generate summary"}), 500

#             batch_ids = []
#             batch_results = []
#             batches = anthropic.split_batch(requests)
#             for batch in batches:
#                 result = await anthropic.create_batch(batch)
#                 batch_ids.append(result["batch_id"])

#             poll_results = await asyncio.gather(*[anthropic.poll_and_fetch_batch_results(batch_id) for batch_id in batch_ids])
#             batch_results.extend(poll_results)

#             if len(batch_results) == 0:
#                 await db.update_section_summary_status(spec_id, section_number, "error")
#                 return jsonify({"error": "Failed to generate summary"}), 500

#             for result in batch_results:
#                 if result.get("status") == "success":
#                     section_id = await db.save_section_summary(spec_id, {
#                         **result.get("content"),
#                         "section_id": section.get("id"),
#                     })
#                     if not section_id:
#                         await db.update_section_summary_status(spec_id, section_number, "error")
#                         return jsonify({"error": "Failed to save section summary"}), 500
#                 else:
#                     await db.update_section_summary_status(spec_id, section_number, "error")
#                     return jsonify({"error": result.get("error")}), 400
#             await db.update_section_summary_status(spec_id, section_number, "complete")

#             return jsonify({"spec_summary": batch_results}), 200

#     except Exception as e:
#         await db.update_section_summary_status(spec_id, section_number, "error")
#         logger.error(f"Error getting spec summary: {e}")
#         return jsonify({"error": str(e)}), 500

# update all section summaries for a status to complete
# @summary_routes_bp.route("/update_all_section_summaries/<spec_id>", methods=["GET"])
# async def update_all_section_summaries(spec_id: str):
#     try:
#         all_sections = await db.get_all_sections_without_primary_pages(spec_id)
#         for section in all_sections:
#             await db.update_section_summary_status(spec_id, section["section_number"], "manual")
#         return jsonify({"all_sections": all_sections}), 200
#     except Exception as e:
#         logger.error(f"Error updating all section summaries: {e}")
#         return jsonify({"error": str(e)}), 500
