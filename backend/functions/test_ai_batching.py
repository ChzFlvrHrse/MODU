from __future__ import annotations
import logging
import asyncio
import os
import dotenv
import aiohttp
import json
from classes.s3_buckets import S3Bucket
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from classes.anthropic import Anthropic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic = Anthropic()
client = anthropic.client


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


system_prompt = """
You are classifying construction specification pages.

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

Note: You may only see the first 2-3 pages of a longer section. If those pages show clear PRIMARY indicators, classify as primary.
"""

dict_pages = {
    "10": {
        "101110": {
            "multi": [],
            "single": [
                43
            ],
            "title": "Undocumented Section Number (MSF2020)"
        },
        "102030": {
            "multi": [
                [
                    60,
                    61,
                    62,
                    63
                ]
            ],
            "single": [],
            "title": "Undocumented Section Number (MSF2020)"
        },
        "102236": {
            "multi": [],
            "single": [
                4
            ],
            "title": "Coiling Partitions"
        },
        "102239": {
            "multi": [
                [
                    436,
                    437,
                    438,
                    439,
                    440,
                    441,
                    442
                ]
            ],
            "single": [],
            "title": "Folding Panel Partitions"
        },
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
    },
    "12": {
        "120039": {
            "multi": [
                [
                    45,
                    46,
                    47,
                    48
                ]
            ],
            "single": [],
            "title": "Undocumented Section Number (MSF2020)"
        },
        "121713": {
            "multi": [],
            "single": [
                39
            ],
            "title": "Etched Glass"
        },
        "122413": {
            "multi": [
                [
                    446,
                    447,
                    448,
                    449
                ]
            ],
            "single": [
                4
            ],
            "title": "Roller Window Shades"
        },
        "123553": {
            "multi": [
                [
                    450,
                    451,
                    452,
                    453,
                    454,
                    455,
                    456,
                    457
                ]
            ],
            "single": [
                4
            ],
            "title": "Laboratory Casework"
        }
    }
}


# ------------------------------------------------------------- batch testing -------------------------------------------------------------

# spec_id = "e6c9865f-7908-4eda-ad95-e1ae7b070bf8"
# s3 = S3Bucket()


# async def main():
#     results = []
#     batch_ids = []

#     async with s3.s3_client() as s3_client:
#         result = await anthropic.batch_requests(dict_pages, spec_id, system_prompt, s3, s3_client, schema=PageClassification)
#         for batch in result:
#             batch_ids.append(batch["batch_id"])
#             results.append(batch)


#         poll_results = await asyncio.gather(*[anthropic.poll_and_fetch_batch_results(batch_id) for batch_id in batch_ids])
#         results.extend(poll_results)
#     return results

# print(asyncio.run(main()))
