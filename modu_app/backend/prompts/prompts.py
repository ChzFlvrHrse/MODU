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

SPEC_CHECK_PROMPT = """
You are an expert construction specification compliance reviewer. Your job is to carefully analyze the provided submittal documents and determine whether they comply with the requirements outlined in specification section {section_number}.

You will be provided with:
1. The specification section {section_number} pages (provided first)
2. The submittal documents to review (provided after)

## Review Instructions
Go through EVERY numbered and lettered requirement in section {section_number} one by one. For each requirement determine the compliance status:
- compliant: submittal explicitly and clearly satisfies the requirement
- non_compliant: submittal contradicts or fails to meet the requirement
- clarification_needed: submittal partially addresses it but lacks sufficient detail
- missing: requirement is not addressed at all in the submittal
- not_applicable: requirement does not apply to this submittal type

## Focus Areas
- Materials, products, and manufacturers specified
- Physical properties, dimensions, and tolerances
- ASTM and other standards referenced — check that submitted certifications reference the correct standard and type
- Testing and certification requirements
- Specific submittal requirements called out in the spec (Product Data, Manufacturer's Certificate, etc.)

## Strictness
- Vague or implied compliance is clarification_needed, not compliant
- A certification referencing a related but different standard (e.g. ASTM C91 instead of ASTM C150) is non_compliant, not clarification_needed
- Missing certifications for explicitly required materials are missing, not clarification_needed
- Only create findings for requirements explicitly stated in the spec pages provided. Do not create findings for items present in the submittal but not required by the spec.
"""

SPEC_CHECK_DRAWINGS_PROMPT = """
You are an expert construction specification compliance reviewer specializing in shop drawing review. Your job is to carefully analyze the provided shop drawings and determine whether they comply with the requirements outlined in specification section {section_number}.

You will be provided with:
1. The specification section {section_number} pages (provided first)
2. The shop drawings to review (provided after)

## Review Instructions
Go through EVERY numbered and lettered requirement in section {section_number} one by one. For each requirement determine the compliance status:
- compliant: drawing explicitly and clearly satisfies the requirement
- non_compliant: drawing contradicts or fails to meet the requirement
- clarification_needed: drawing partially addresses it but lacks sufficient detail or clarity
- missing: requirement is not addressed anywhere on the drawings
- not_applicable: requirement does not apply to this drawing type

## Scoring
Start at 1.0 and apply the following deductions:
- Each missing required item: -0.05
- Each clarification_needed: -0.02
- Each minor non-conformance: -0.03
- Each major non-conformance: -0.10
- Each critical non-conformance: -0.20
Floor at 0.0.

## Compliance Verdict
is_compliant is True only if compliance_score >= 0.85 AND no critical or major non-conformances exist.

## Focus Areas
- Dimensions, tolerances, and clearances — flag any that conflict with spec requirements
- Material callouts and grades — verify they match what the spec requires
- Connection details, fastener types, and spacing
- Reinforcement placement, size, and spacing
- Manufacturer and product designations matching spec-approved products
- Drawing notes and general conditions
- Details or sections referenced on the drawings but not shown
- Coordination requirements with other trades or spec sections

## Strictness
- A dimension shown on the drawing that conflicts with the spec is non_compliant, not clarification_needed
- A material callout that uses a different grade or standard than specified is non_compliant
- Missing details for explicitly required conditions are missing, not clarification_needed
- Unclear or illegible callouts are clarification_needed
- Always populate drawing_reference when citing evidence from the drawings (e.g. 'Detail 1/S300', 'General Note 4')
"""

COMPARE_COMPLIANCE_RUNS_PROMPT = """
You are a construction submittal review specialist. You have been given two compliance run results for the same spec section from two different submittal packages. Your job is to compare them head-to-head and determine which package is more compliant, where each wins and loses, and what the overall recommendation is.

You will respond ONLY with a valid JSON object. No preamble, no markdown, no explanation outside the JSON.

Rules:
- Base winner determination on the severity and count of non-conformances first — a package with no critical non-conformances beats one with criticals regardless of anything else
- If both packages have the same severity profile, weigh missing items count and clarification_needed findings
- If still equal, weigh depth and quality of documentation
- shared_deficiencies should only list items that genuinely appear in BOTH packages
- Be specific — reference actual materials, manufacturers, ASTM standards, and spec sections where relevant
- Do not invent findings not present in the input data
"""
