from pydantic import BaseModel, Field

def make_classification_schema(section_number: str) -> type[BaseModel]:
    class PageClassification(BaseModel):
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
    return PageClassification


def make_summary_schema(section_number: str) -> type[BaseModel]:
    _sec = section_number

    class SectionSummary(BaseModel):
        section_number: str = Field(
            description=f"The section number being summarized for section {_sec}")
        section_title: str = Field(description="The section title")
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
