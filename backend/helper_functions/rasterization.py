import fitz, logging, asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rasterize_page(doc: fitz.Document, page_index: int, dpi: int = 200) -> bytes:
    page = doc.load_page(page_index)

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")

async def rasterize_pdf(pdf_path: str, dpi: int = 200, start_page: int = 0, end_page: int = None) -> list[dict[int, bytes]]:
    doc = fitz.open(pdf_path)
    try:
        if end_page is None:
            end_page = len(doc) - 1

        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        for page_index in range(start_page, end_page + 1):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            yield {"page_index": page_index, "bytes": png_bytes}
    finally:
        doc.close()

print(asyncio.run(rasterize_pdf(pdf_path="example_spec.pdf", dpi=200, start_page=88, end_page=103)))
