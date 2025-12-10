from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os, logging, base64, asyncio
from classes.s3_buckets import S3Bucket
from typing import Optional, Tuple, List

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Property(BaseModel):
    name: str = Field(
        description=(
            "The name of the technical property or requirement. "
            "Examples: 'compressive_strength', 'U_value', 'R_value', 'wattage', "
            "'voltage', 'fire_rating', 'sound_transmission_class'."
        )
    )
    value: Optional[str] = Field(
        default=None,
        description=(
            "The reported value of the property exactly as written. "
            "Keep as a raw string. Example: '3000 psi', '0.32', '1-hour', '120V'."
        )
    )
    units: Optional[str] = Field(
        default=None,
        description=(
            "The units for the numeric value if separable. Examples: 'psi', 'W/m²K', "
            "'hr', 'V', 'BTU/hr'. Leave null if unclear or not present."
        )
    )
    context: Optional[str] = Field(
        default=None,
        description=(
            "Additional context, test conditions, or qualifiers. "
            "Examples: 'at 28 days', 'minimum', 'average', 'UL listed', 'ASTM tested'."
        )
    )

class ProductSpec(BaseModel):
    product_name: str = Field(
        description=(
            "The name/model of the product or material as written in the submittal. "
            "Examples: 'SPEC MIX Core-Fill Grout', 'York CMU', 'FireLite Door 90-Minute', "
            "'Lutron LED Driver'."
        )
    )
    manufacturer: Optional[str] = Field(
        default=None,
        description=(
            "The manufacturer name if present. Example: 'SPEC MIX', 'Owens Corning', 'Siemens'."
        )
    )
    material_category: Optional[str] = Field(
        default=None,
        description=(
            "A broad classification of the product. Examples: "
            "'masonry', 'grout', 'concrete', 'door', 'window', 'HVAC unit', "
            "'air handler', 'lighting fixture', 'electrical cable', 'fire alarm device'. "
            "AI should infer this if reasonably certain."
        )
    )
    csi_division: Optional[str] = Field(
        default=None,
        description=(
            "The CSI division the product belongs to, if known. Example: '04', '05', '08', '23', '26'. "
            "Do NOT guess if not clearly stated."
        )
    )
    spec_section: Optional[str] = Field(
        default=None,
        description=(
            "The project specification section number this product falls under (if mentioned). "
            "Examples: '042000', '260519', '233113'."
        )
    )
    document_type: Optional[str] = Field(
        default=None,
        description=(
            "The type of submittal document. Examples: 'product_data', 'shop_drawing', "
            "'test_report', 'mockup_photos', 'manufacturer_letter', 'UL listing', 'ICC report'."
        )
    )
    standards: List[str] = Field(
        default_factory=list,
        description=(
            "List of referenced standards the product claims conformance to. "
            "Examples: ['ASTM C90', 'UL 10C', 'NFPA 72', 'ASTM E119', 'IES LM-79']."
        )
    )
    properties: List[Property] = Field(
        default_factory=list,
        description=(
            "All extracted technical or performance properties associated with this product. "
            "This includes physical properties, mechanical properties, electrical ratings, "
            "fire ratings, thermal values, dimensions, tolerances, etc."
        )
    )
    notes: str = Field(
        default="",
        description=(
            "Any additional relevant notes or observations. "
            "Should not repeat property names or standards — use only for supplemental context."
        )
    )
    document_pages: List[int] = Field(
        default_factory=list,
        description=(
            "List of 0-based page numbers where this product appears. "
            "This allows mapping product specs back to the original PDF."
        )
    )

class SpecReqs(BaseModel):
    spec_section: Optional[str] = Field(
        default=None,
        description=(
            "The project specification section this submittal is intended to satisfy. "
            "Usually given by the contractor: e.g., '042000', '260519'. "
            "If unknown, leave null."
        )
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Name of the project if found within the document."
    )
    products: List[ProductSpec] = Field(
        default_factory=list,
        description=(
            "List of all products or materials extracted from the submittal. "
            "Each product may span multiple pages of the document."
        )
    )
    notes: str = Field(
        default="",
        description="General notes or uncertainties about the submittal extraction."
    )

# async def extract_specs_from_text_page(page_text: str, page_index: int) -> SpecReqs:
#     prompt = """
# You are reading a construction submittal (any trade: masonry, doors, HVAC, electrical, etc.).

# Extract ALL products and their technical specifications from this text and
# return them in the SpecReqs schema.

# - products[] should include every distinct product or material.
# - For each product, include:
#   - product_name, manufacturer, material_category (best guess), spec_section/csi_division if shown
#   - all applicable standards (ASTM, UL, NFPA, IES, etc.)
#   - properties[] for any performance/value requirement (strength, R-value, U-value,
#     size ranges, voltages, wattage, sound ratings, coatings, etc.)
# Do NOT invent values that are not present. It's OK to leave value or units null.
# Only return valid JSON.
# """

#     res = await client.beta.chat.completions.parse(
#         model="gpt-4.1",
#         response_format=SpecReqs,
#         messages=[
#             {"role": "user", "content": prompt + "\n\nTEXT:\n" + page_text}
#         ],
#         temperature=0.0
#     )

#     result = res.choices[0].message
#     specs = result.parsed if hasattr(result, "parsed") else json.loads(result.content)
#     for p in specs.products:
#         p.document_pages.append(page_index)
#     return specs.model_dump()


# async def extract_specs_from_image_page(image_bytes: bytes, page_index: int) -> SpecReqs:
#     prompt = """
# You are reading a construction submittal (any trade: masonry, doors, HVAC, electrical, etc.).

# From this PAGE IMAGE, extract ALL visible products and technical specifications
# and return them in the SpecReqs schema.


# Include data from:
# - product data sheets
# - test reports
# - manufacturer letters
# - certification tables

# Rules:
# - If the product is not clear, infer the closest match from visible text.
# - Include standards (ASTM, ANSI, UL, NFPA) wherever they appear.
# - Include performance values (compressive strength, R-values, etc.)
# - Never hallucinate missing info — only extract what's visible.
# - Include all relevant data even if partially cut off.

# Only return valid JSON.
# """

#     res = await client.beta.chat.completions.parse(
#         model="gpt-4.1",
#         response_format=SpecReqs,
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": prompt},
#                     {
#                         "type": "image_url",
#                         "image_url": {
#                             "url": "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8")
#                         }
#                     }
#                 ]
#             }
#         ],
#         temperature=0.0
#     )

#     result = res.choices[0].message
#     specs = result.parsed if hasattr(result, "parsed") else None
#     for p in specs.products:
#         p.document_pages.append(page_index)
#     return specs.model_dump()

async def extract_section_requirements_from_pages(pages: list[dict]) -> dict:
    """
    pages: list of {"page_index", "text", "bytes"} from S3/hybrid_pdf
    Returns a single SectionRequirements/SubmittalSpecs-style dict.
    """
    # Split into primary + context by longest contiguous run
    indices = [p["page_index"] for p in pages]
    primary_indices = set(longest_contiguous_run(indices))

    primary_pages = [p for p in pages if p["page_index"] in primary_indices]
    context_pages = [p for p in pages if p["page_index"] not in primary_indices]

    content_blocks = [
        {
            "type": "text",
            "text": (
                "You are reading multiple PAGES from a single specification SECTION.\n\n"
                "Use ALL of the PRIMARY pages together to extract the requirements.\n"
                "Other pages are only references to this section (TOC, cross-references) "
                "and should be treated as secondary context.\n"
                "Pages are labeled below.\n\n"
                "FIRST: PRIMARY PAGES (contain the section body and requirements).\n"
                "If a page includes both text and an image, the image is the same page as "
                "the text and should only be used to supplement or correct missing text "
                "(tables, formatting, cut-off words), not as a separate data source.\n"
            ),
        }
    ]

    def add_page_block(page: dict, label: str):
        idx = page["page_index"]
        text = page["text"]
        bytes_ = page["bytes"]

        if text:
            content_blocks.append(
                {
                    "type": "text",
                    "text": f"\n\n===== {label} PAGE {idx} START =====\n{text}\n===== {label} PAGE {idx} END =====\n",
                }
            )
        if bytes_:
            content_blocks.append(
                {
                    "type": "text",
                    "text": f"\n\n===== {label} PAGE {idx} (IMAGE) START =====\n",
                }
            )
            content_blocks.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,"
                        + base64.b64encode(bytes_).decode("utf-8")
                    },
                }
            )
            content_blocks.append(
                {
                    "type": "text",
                    "text": f"\n===== {label} PAGE {idx} (IMAGE) END =====\n",
                }
            )

    for page in primary_pages:
        add_page_block(page, "PRIMARY")

    if context_pages:
        content_blocks.append(
            {
                "type": "text",
                "text": (
                    "\n\nNEXT: CONTEXT PAGES (TOC or cross-references; "
                    "only use them if they help you identify the section number/title).\n"
                ),
            }
        )
        for page in context_pages:
            add_page_block(page, "CONTEXT")

    prompt = """
You are reading a construction SPECIFICATION SECTION that may be spread across
multiple pages.

PRIMARY pages contain the actual body of the section and its requirements.
CONTEXT pages are table-of-contents or cross-reference pages.

Your job:
- Treat all PRIMARY pages as one continuous section.
- Use CONTEXT pages only to confirm the section number, title, and project name.
- Extract all requirements/products and return a single JSON object in the given schema.
- Merge duplicates across pages.

Only return valid JSON.
"""

    res = await client.beta.chat.completions.parse(
        model="gpt-4.1",
        response_format=SpecReqs,   # or SectionRequirements if you switch
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}, *content_blocks],
            }
        ],
        temperature=0.0,
    )

    specs = res.choices[0].message.parsed

    # Attach explicit page indices for traceability
    all_primary_indices = [p["page_index"] for p in primary_pages]
    for p in specs.products:
        existing = getattr(p, "document_pages", [])
        p.document_pages = sorted(set(existing + all_primary_indices))

    return specs.model_dump()


def longest_contiguous_run(page_indices: list[int]) -> list[int]:
    if not page_indices:
        return []

    best_run = []
    current_run = [page_indices[0]]

    for p in page_indices[1:]:
        if p == current_run[-1] + 1:
            current_run.append(p)
        else:
            if len(current_run) > len(best_run):
                best_run = current_run
            current_run = [p]

    if len(current_run) > len(best_run):
        best_run = current_run

    return best_run

async def merge_submittal_results(results: list[dict]) -> dict:
    merged = {
        "spec_section": None,
        "project_name": None,
        "products": [],
        "notes": ""
    }

    # simple product dedupe by (name, manufacturer)
    index = {}
    for res in results:
        if res["notes"]:
            merged["notes"] += f"{res['notes']} "

        for p in res["products"]:
            key = (p["product_name"].strip().lower(), (p["manufacturer"] or "").strip().lower())
            if key not in index:
                index[key] = p
                merged["products"].append(p)
            else:
                existing = index[key]
                # merge pages
                existing["document_pages"] = sorted(
                    set(existing["document_pages"] + p["document_pages"])
                )
                # merge standards & properties without duplicates
                for s in p["standards"]:
                    if s not in existing["standards"]:
                        existing["standards"].append(s)
                existing["properties"].extend(p["properties"])  # later you can dedupe by name

    merged['notes'] = merged['notes'].strip()

    return merged

async def section_spec_requirements(spec_id: str, section_pages: list[int]) -> dict:
    s3 = S3Bucket()
    section_pages = s3.get_section_pages(spec_id, section_pages)

    extracted_specs = await extract_section_requirements_from_pages(section_pages)

    # return await merge_submittal_results(per_page_results)
    return extracted_specs

# s3 = S3Bucket()
# spec_id = "2ad9cd93-2a40-4b3e-a11c-e52decfe0e6c"
# pages = [2, 76, 89, 90, 91, 92, 93, 94, 95, 96, 103]

# print(asyncio.run(section_spec_requirements(spec_id, pages)))
