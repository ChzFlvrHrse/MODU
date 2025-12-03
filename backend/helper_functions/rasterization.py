import fitz, logging, asyncio
from typing import AsyncIterator, TypedDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rasterize_page(doc: fitz.Document, page_index: int, dpi: int = 200) -> bytes:
    page = doc.load_page(page_index)

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")

class RasterizedPage(TypedDict):
    page_index: int
    bytes: bytes

async def rasterize_pdf(pdf_path: str, dpi: int = 200, start_index: int = 0, end_index: int = None) -> AsyncIterator[RasterizedPage]:
    doc = fitz.open(pdf_path)
    try:
        if end_index is None:
            end_index = len(doc) - 1

        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        for page_index in range(start_index, end_index + 1):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            logger.info(f"Rasterized page {page_index}")
            yield {"page_index": page_index, "bytes": png_bytes}
    finally:
        doc.close()

# async def rasterize(pdf_path: str, dpi: int = 200, start_page: int = 0, end_page: int = None) -> AsyncIterator[dict[int, bytes]]:
#     async for page in rasterize_pdf(pdf_path, dpi=dpi, start_page=start_page, end_page=end_page):
#         logger.info(f"Rasterized page {page['page_index']}")
#         yield page
