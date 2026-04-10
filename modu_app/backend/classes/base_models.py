from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# ------------------------------------------------------------ Classification Schema ------------------------------------------------------------


def make_classification_schema(section_number: str) -> type[BaseModel]:
    class PageClassification(BaseModel):
        section_title: str = Field(
            description=f"The title of the section being classified for section {section_number}"
        )
        reasoning: str = Field(
            description="Brief explanation of the classification decision"
        )
        pages_analyzed: list[int] = Field(
            description="List of page numbers that were analyzed"
        )
        confidence: float = Field(
            description="Confidence level in the classification between 0 and 1"
        )
        is_primary: bool = Field(
            description=f"True ONLY if the page contains the primary specification body for section {section_number} specifically. Must be false if reasoning concludes content belongs to a different section."
        )
        referenced_sections: list[str] = Field(
            default_factory=list,
            description="List of other CSI MasterFormat section numbers explicitly referenced in this page or block (e.g. ['033000', '011000']). Empty list if none found."
        )
    return PageClassification

# ------------------------------------------------------------ Summary Schema ------------------------------------------------------------


def make_summary_schema(section_number: str) -> type[BaseModel]:
    _sec = section_number

    class SectionSummary(BaseModel):
        section_number: str = Field(
            description=f"The section number being summarized for section {_sec}")
        section_title: str = Field(
            description=f"The title of the section being classified for section {_sec}")
        overview: str = Field(
            description=f"Brief overview of what this section covers for section {_sec}")
        key_requirements: list[str] = Field(
            description="Key technical requirements and standards")
        materials: list[str] = Field(
            description="Specified materials and products")
        submittals: list[str] = Field(
            description="Required submittals and shop drawings")
        testing: list[str] = Field(
            description="Testing and inspection requirements")
        related_sections: list[str] = Field(
            description="Related sections referenced in the spec")
    return SectionSummary

# ------------------------------------------------------------ Spec Check Schema ------------------------------------------------------------


class RequirementFinding(BaseModel):
    requirement: str = Field(
        description="The specific requirement from the specification being evaluated."
    )
    status: str = Field(
        description=(
            "Compliance status: 'compliant', 'non_compliant', 'clarification_needed', "
            "'missing', 'not_applicable'."
        )
    )
    evidence: Optional[str] = Field(
        default=None,
        description=(
            "Direct evidence from the submittal or drawing that supports or "
            "contradicts this requirement."
        )
    )
    spec_reference: Optional[str] = Field(
        default=None,
        description=(
            "The specific section and paragraph reference in the spec where "
            "this requirement is stated (e.g. 'Section 2.3.B.1')."
        )
    )
    drawing_reference: Optional[str] = Field(
        default=None,
        description=(
            "Specific detail, section, or callout on the drawing where evidence "
            "was found (e.g. 'Detail 1/S300', 'Section A'). Only populated for "
            "shop drawing reviews."
        )
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional context or clarification about this finding."
    )
    spec_pages: List[int] = Field(
        default_factory=list,
        description="0-based page numbers in the spec where this requirement appears."
    )
    submittal_pages: List[int] = Field(
        default_factory=list,
        description="0-based page numbers in the submittal where evidence was found."
    )


class NonConformance(BaseModel):
    description: str = Field(
        description="Clear description of the non-conformance."
    )
    severity: str = Field(
        description="Severity level: 'critical', 'major', 'minor', 'informational'."
    )
    spec_reference: Optional[str] = Field(
        default=None,
        description="The specific spec clause or section this non-conformance relates to."
    )
    recommendation: Optional[str] = Field(
        default=None,
        description="Recommended corrective action."
    )


class MissingItem(BaseModel):
    description: str = Field(
        description="Description of the missing information or document."
    )
    spec_reference: Optional[str] = Field(
        default=None,
        description="The specific spec clause requiring this item."
    )
    required: bool = Field(
        default=True,
        description=(
            "Whether this item is explicitly required by the spec (True) "
            "or recommended but not mandatory (False)."
        )
    )


def make_spec_check_schema(section_number: str) -> type[BaseModel]:
    class SpecCheck(BaseModel):
        is_compliant: bool = Field(
            description=(
                f"Overall compliance verdict for section {section_number}. "
                "True only if compliance_score >= 0.85 AND no critical or "
                "major non-conformances exist."
            )
        )
        # compliance_score: float = Field(
        #     description=(
        #         f"Compliance score for section {section_number} from 0.0 to 1.0. "
        #         "Calculated by starting at 1.0 and applying deductions: "
        #         "missing required item -0.05, clarification_needed -0.02, "
        #         "non_compliant minor -0.03, non_compliant major -0.10, "
        #         "non_compliant critical -0.20. Floor at 0.0."
        #     )
        # )
        summary: str = Field(
            description=(
                f"3-5 sentence executive summary of the compliance review for "
                f"section {section_number}. Should state the overall disposition, "
                "the most critical issues, and whether the submittal is approvable "
                "as-is, approvable with comments, or requires resubmittal."
            )
        )
        requirement_findings: List[RequirementFinding] = Field(
            default_factory=list,
            description=(
                f"Detailed findings for each requirement found in section "
                f"{section_number}. Every explicit spec requirement should have "
                "a corresponding entry."
            )
        )
        non_conformances: List[NonConformance] = Field(
            default_factory=list,
            description=(
                f"List of identified non-conformances against section "
                f"{section_number} requirements, ordered by severity descending."
            )
        )
        missing_items: List[MissingItem] = Field(
            default_factory=list,
            description=(
                f"Items explicitly required by section {section_number} that "
                "are absent from the submittal."
            )
        )
        recommendations: List[str] = Field(
            default_factory=list,
            description=(
                f"Actionable recommendations for the contractor to achieve "
                f"compliance with section {section_number}, ordered by priority "
                "descending (most critical first)."
            )
        )
        reviewer_notes: str = Field(
            default="",
            description=(
                f"Additional observations noted during review of section "
                f"{section_number}. Use for scope observations, voluntary "
                "additional documentation notes, or flags for structural/MEP "
                "engineer review that fall outside the spec reviewer's scope."
            )
        )
    return SpecCheck

# ------------------------------------------------------------ Compare Compliance Runs Schema ------------------------------------------------------------


class DimensionComparison(BaseModel):
    dimension: str = Field(
        description="The requirement or category being compared (e.g. 'CMU certification', 'joint reinforcement documentation')."
    )
    winner: Literal["A", "B", "tie"] = Field(
        description="Which package wins this dimension, or tie if equivalent."
    )
    a_status: Literal["compliant", "non_compliant", "missing", "partial", "clarification_needed", "unclear"] = Field(
        description="Compliance status of package A for this dimension."
    )
    b_status: Literal["compliant", "non_compliant", "missing", "partial", "clarification_needed", "unclear"] = Field(
        description="Compliance status of package B for this dimension."
    )
    rationale: str = Field(
        description="1-2 sentences explaining why one package wins this dimension over the other."
    )


def make_compare_compliance_runs_schema(section_number: str) -> type[BaseModel]:

    class ComplianceComparison(BaseModel):
        overall_winner: Literal["A", "B", "tie"] = Field(
            description=(
                f"The package with superior overall compliance for section {section_number}. "
                "Determine the winner using this hierarchy: "
                "(1) Fewer critical non-conformances wins — a package with zero criticals always beats one with criticals. "
                "(2) If equal on criticals, fewer major non-conformances wins. "
                "(3) If equal on criticals and majors, fewer missing required items wins. "
                "(4) If still equal, fewer clarification_needed findings wins. "
                "(5) If all equal, better documentation depth and quality wins. "
                "Declare a tie only if packages are genuinely equivalent across all five criteria."
            )
        )
        confidence: Literal["high", "medium", "low"] = Field(
            description="Confidence in the comparison. Low if both packages have extensive missing items making meaningful comparison difficult."
        )
        executive_summary: str = Field(
            description=f"2-3 sentence plain-language summary of which package wins section {section_number} and the primary reasons why."
        )
        dimension_comparisons: List[DimensionComparison] = Field(
            default_factory=list,
            description=f"Head-to-head comparison for each major requirement or documentation category in section {section_number}."
        )
        a_exclusive_strengths: List[str] = Field(
            default_factory=list,
            description="Things package A does well that package B does not."
        )
        b_exclusive_strengths: List[str] = Field(
            default_factory=list,
            description="Things package B does well that package A does not."
        )
        shared_deficiencies: List[str] = Field(
            default_factory=list,
            description=f"Non-conformances or missing items present in both packages for section {section_number}."
        )
        a_critical_failures: List[str] = Field(
            default_factory=list,
            description="Critical or major non-conformances unique to package A."
        )
        b_critical_failures: List[str] = Field(
            default_factory=list,
            description="Critical or major non-conformances unique to package B."
        )
        recommendation: str = Field(
            description=f"Actionable recommendation for section {section_number} — which package to prefer, what the losing package must resubmit to become competitive, and whether either package is approvable as-is."
        )
    return ComplianceComparison
