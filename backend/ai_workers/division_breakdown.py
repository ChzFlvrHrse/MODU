import os
import logging
from openai import OpenAI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Division(BaseModel):
    division_code: str = Field(description="CSI division code (e.g., '03')")
    division_name: str = Field(description="Name of the division (e.g., 'Concrete')")
    page_range: list[int] = Field(description="Start and end page numbers", default=[])
    scope_summary: str = Field(description="Summary of the scope for this division", default="")
    assumptions_or_risks: list[str] = Field(description="List of assumptions or risks identified", default=[])
    keywords_found: list[str] = Field(description="Relevant keywords found in the spec", default=[])

class DivisionBreakdown(BaseModel):
    divisions_detected: list[Division] = Field(description="A list of detected divisions", default=[])
    notes: str = Field(description="Any uncertainty or questions", default="")

def division_breakdown(spec_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4.1",
        response_format=DivisionBreakdown,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert construction estimator. "
                    "Given a section of a spec sheet, your job is to detect which CSI divisions are present "
                    "and extract only what is relevant to each division. "
                    "You must ALWAYS respond as valid JSON with this structure:\n"
                    "{\n"
                    "  'divisions_detected': [\n"
                    "     {\n"
                    "       'division_code': '03',\n"
                    "       'division_name': 'Concrete',\n"
                    "       'page_range': [start, end],\n"
                    "       'scope_summary': '...summary...',\n"
                    "       'assumptions_or_risks': ['...'],\n"
                    "       'keywords_found': ['rebar', 'slab']\n"
                    "     }\n"
                    "  ],\n"
                    "  'notes': 'Any uncertainty or questions'\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": spec_text
            },
        ]
    )

    return response.choices[0].message.content
