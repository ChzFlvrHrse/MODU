from typing import Optional
from dataclasses import dataclass

@dataclass
class HybridPage():
    page_index: int
    text: str
    bytes: Optional[bytes]

@dataclass
class PdfPageConverterResult():
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
