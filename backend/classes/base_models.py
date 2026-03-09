from pydantic import BaseModel, Field
from typing import Optional, List

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
        description="Compliance status: 'compliant', 'non_compliant', 'missing', 'unclear'."
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Direct evidence from the submittal or drawing that supports or contradicts this requirement."
    )
    drawing_reference: Optional[str] = Field(
        default=None,
        description="Specific detail, section, or callout on the drawing where evidence was found (e.g. 'Detail 1/S300', 'Section A'). Only populated for shop drawing reviews."
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
        description="Severity level: 'critical', 'major', 'minor'."
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
        description="Whether this item is explicitly required by the spec or recommended."
    )


def make_spec_check_schema(section_number: str) -> type[BaseModel]:
    class SpecCheck(BaseModel):
        is_compliant: bool = Field(
            description=f"Overall compliance verdict for section {section_number}. True only if no critical non-conformances exist."
        )
        compliance_score: float = Field(
            description=f"Compliance score for section {section_number} from 0.0 to 1.0 where 1.0 is fully compliant."
        )
        summary: str = Field(
            description=f"High level summary of the compliance review for section {section_number}."
        )
        requirement_findings: List[RequirementFinding] = Field(
            default_factory=list,
            description=f"Detailed findings for each requirement found in section {section_number}."
        )
        non_conformances: List[NonConformance] = Field(
            default_factory=list,
            description=f"List of identified non-conformances against section {section_number} requirements."
        )
        missing_items: List[MissingItem] = Field(
            default_factory=list,
            description=f"Items required by section {section_number} that are absent from the submittal."
        )
        recommendations: List[str] = Field(
            default_factory=list,
            description=f"Actionable recommendations for the contractor to achieve compliance with section {section_number}."
        )
        reviewer_notes: str = Field(
            default="",
            description=f"Any additional observations or uncertainties noted during review of section {section_number}."
        )
    return SpecCheck
