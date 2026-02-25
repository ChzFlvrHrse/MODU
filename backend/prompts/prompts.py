from pydantic import BaseModel, Field

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


SUMMARY_PROMPT = """
You are extracting structured information from construction specification pages for section {section_number}.

Given the pages provided, extract a comprehensive summary of section {section_number} including:
- A brief overview of what the section covers
- Key technical requirements and standards that must be met
- Specified materials and products
- Required submittals and shop drawings
- Testing and inspection requirements
- Related sections referenced in the spec

Be concise and specific. Extract only what is explicitly stated in the pages — do not infer or add information not present in the document.

If a field has no relevant content in the provided pages, return an empty list or empty string.
"""
