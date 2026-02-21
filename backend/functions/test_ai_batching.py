from __future__ import annotations
import json
import aiohttp
from classes.s3_buckets import S3Bucket
from anthropic import AsyncAnthropic, RateLimitError
from dotenv import load_dotenv
import os
import logging
import asyncio
from pydantic import BaseModel, Field
from classes import db
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

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

dict_pages = {
    # "101110": {
    #     "multi": [],
    #     "single": [
    #         43
    #     ],
    #     "title": "Undocumented Section Number (MSF2020)"
    # },
    # "102030": {
    #     "multi": [
    #         [
    #             60,
    #             61,
    #             62,
    #             63
    #         ]
    #     ],
    #     "single": [],
    #     "title": "Undocumented Section Number (MSF2020)"
    # },
    # "102236": {
    #     "multi": [],
    #     "single": [
    #         4
    #     ],
    #     "title": "Coiling Partitions"
    # },
    # "102239": {
    #     "multi": [
    #         [
    #             436,
    #             437,
    #             438,
    #             439,
    #             440,
    #             441,
    #             442
    #         ]
    #     ],
    #     "single": [],
    #     "title": "Folding Panel Partitions"
    # },
    "104320": {
        "multi": [],
        "single": [
            63
        ],
        "title": "Undocumented Section Number (MSF2020)"
    },
    "104400": {
        "multi": [
            [
                443,
                444,
                445
            ]
        ],
        "single": [
            4
        ],
        "title": "Fire Protection Specialties"
    }
}


# A single page payload: (page_index, text, optional_image_bytes)
PagePayload = Tuple[int, str, Optional[bytes]]


def _enforce_no_additional_properties(schema: Dict[str, Any]) -> None:
    if schema.get("type") == "object":
        schema.setdefault("additionalProperties", False)
    for value in schema.get("properties", {}).values():
        if isinstance(value, dict):
            _enforce_no_additional_properties(value)
    for sub in schema.get("$defs", {}).values():
        if isinstance(sub, dict):
            _enforce_no_additional_properties(sub)


def _page_blocks(page_index: int, text: str, image_bytes: Optional[bytes]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = [
        {"type": "text", "text": f"===== PAGE {page_index} TEXT ====="},
        {"type": "text", "text": text or ""},
    ]

    if image_bytes:
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_bytes,
            },
        })
    return blocks


def build_claude_request(custom_id: str, section_number: str, pages: Sequence[PagePayload]) -> Dict[str, Any]:
    # Build a single user message containing multi and single page content blocks
    content_blocks: List[Dict[str, Any]] = []
    pages_analyzed = []
    for page_index, text, img in pages:
        pages_analyzed.append(page_index)
        content_blocks.extend(_page_blocks(page_index, text, img))

    content_blocks.insert(
        0,
        {
            "type": "text",
            "text": f"Section number being analyzed: {section_number}. Pages provided: {pages_analyzed}. Set pages_analyzed exactly to this list.",
        },
    )

    schema = PageClassification.model_json_schema()
    if "type" not in schema:
        schema["type"] = "object"
    _enforce_no_additional_properties(schema)

    return {
        "custom_id": str(custom_id),
        "params": {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 1024,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": content_blocks,
                }
            ],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": schema,
                }
            },
        },
    }


async def classify_batch_ai(requests: list[dict]) -> dict:
    try:
        batch = await client.messages.batches.create(requests=requests)

        return {
            "batch_id": batch.id,
            "status": batch.processing_status,
            "request_counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
                "canceled": batch.request_counts.canceled,
                "expired": batch.request_counts.expired,
            },
        }

    except Exception as e:
        logger.error(f"Error classifying batch: {e}")
        return {
            "error": str(e),
            "status": "error",
        }


async def batch_requests(sections: dict[int, dict], spec_id: str, s3: S3Bucket = None, s3_client: any = None) -> list[dict]:
    requests = []

    for section_number, section in sections.items():
        for multi in section.get("multi", []):
            start_index, end_index = multi[:2]
            custom_id = f'{start_index}-{end_index}-{section_number}-{spec_id}'

            page_payloads: List[PagePayload] = []

            async for page in s3.get_converted_pages_generator_with_client(
                spec_id, s3_client, start_index, end_index + 1
            ):
                page_payloads.append(
                    (page["page_index"], page["text"], page["bytes"]))

            claude_request = build_claude_request(
                custom_id, section_number, page_payloads)
            requests.append(claude_request)

        for single in section.get("single", []):
            custom_id = f'{single}-{section_number}-{spec_id}'
            page_payloads: List[PagePayload] = []
            async for page in s3.get_converted_pages_generator_with_client(
                spec_id, s3_client, single, single + 1
            ):
                page_payloads.append(
                    (page["page_index"], page["text"], page["bytes"]))
            claude_request = build_claude_request(
                custom_id, section_number, page_payloads)
            requests.append(claude_request)

    results = await classify_batch_ai(requests)
    return results

# ------------------------------------------------------------- batch testing -------------------------------------------------------------

spec_id = "e6c9865f-7908-4eda-ad95-e1ae7b070bf8"
s3 = S3Bucket()


async def main():
    async with s3.s3_client() as s3_client:
        result = await batch_requests(dict_pages, spec_id, s3, s3_client)
        return result["batch_id"]

batch_id = asyncio.run(main())


async def poll_for_batch_results(batch_id: str) -> dict:
    while True:
        batch_results = await client.messages.batches.retrieve(batch_id)
        logger.info(f"Batch results: {batch_results.processing_status}")
        if batch_results.processing_status == "ended":
            return batch_results
        else:
            await asyncio.sleep(1)

batch_results = asyncio.run(poll_for_batch_results(batch_id))


async def fetch_batch_results(batch_url: str) -> dict:
    try:
        headers = {
            "x-api-key": os.getenv('ANTHROPIC_API_KEY'),
            "anthropic-version": "2023-06-01",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(batch_url, headers=headers) as response:
                response.raise_for_status()

                text = await response.text()
                parsed = []
                for line in text.strip().splitlines():
                    result = json.loads(line)
                    content_str = (
                        result.get("result", {})
                              .get("message", {})
                              .get("content", [{}])[0]
                              .get("text", "{}")
                    )
                    parsed.append({
                        "custom_id": result.get("custom_id"),
                        "content": json.loads(content_str),
                    })
                return parsed
    except Exception as e:
        logger.error(f"Error fetching batch results: {e}")
        return None

batch_url = batch_results.results_url

print(asyncio.run(fetch_batch_results(batch_url)))
