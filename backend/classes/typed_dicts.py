from typing import Optional, TypedDict

class HybridPage(TypedDict):
    page_index: int
    text: Optional[str]
    bytes: Optional[bytes]

class PdfPageConverterResult(TypedDict):
    success_rate: float
    attempted_uploads: int
    successful_uploads: int
    runtime: str
    bucket: str
    spec_id: str
    dpi: int
    grayscale: bool
    rasterize_all: bool
    start_index: int
    end_index: Optional[int]
