import fitz, logging
from typing import Iterator, Optional, TypedDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridPage(TypedDict):
    page_index: int
    text: Optional[str]
    bytes: Optional[bytes]

def rasterize_page(
    doc: fitz.Document,
    page_index: int,
    dpi: int = 200,
    grayscale: bool = True
) -> bytes:
    num_pages = len(doc)

    if num_pages == 0:
        raise ValueError("Document has no pages")

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    colorspace = fitz.csGRAY if grayscale else fitz.csRGB

    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=colorspace)
    png_bytes = pix.tobytes("png")

    logger.info(
        "Rasterized page %d/%d (dpi=%d, size=%dx%d)",
        page_index,
        len(doc) - 1,
        dpi,
        pix.width,
        pix.height
    )
    return png_bytes

def get_text(doc: fitz.Document, page_index: int) -> str:
    page = doc.load_page(page_index)
    return page.get_text("text").strip()

def hybrid_pdf(
    pdf_path: str,
    dpi: int = 200,
    char_threshold: int = 100,
    start_index: int = 0,
    end_index: int = None,
    grayscale: bool = True
) -> Iterator[HybridPage]:

    doc = fitz.open(pdf_path)
    try:
        num_pages = len(doc)

        if num_pages == 0:
            raise ValueError("Document has no pages")
        if start_index < 0:
            raise ValueError("Start index must be greater than or equal to 0")
        if end_index is not None and end_index < 0:
            raise ValueError("End index must be greater than or equal to 0")
        if end_index is not None and end_index >= num_pages:
            raise ValueError("End index must be less than the number of pages in the document")

        start = max(0, start_index)
        stop = min(num_pages - 1, end_index) if end_index is not None else num_pages - 1

        if start > stop:
            raise ValueError("Start index must be less than or equal to end index")

        for page_index in range(start, stop + 1):
            try:
                text = get_text(doc, page_index)

                # Cleaned only for character count threshold check
                clean_text = text.replace(" ", "").replace("\n", " ")

                if len(clean_text) >= char_threshold:
                    logger.info(f"Page {page_index} has {len(clean_text)} characters, skipping rasterization")
                    yield {"page_index": page_index, "text": text, "bytes": None}
                else:
                    logger.info(f"Page {page_index} has {len(clean_text)} characters, rasterizing")
                    yield {"page_index": page_index, "text": None, "bytes": rasterize_page(doc, page_index, dpi, grayscale=grayscale)}
            except ValueError as e:
                logger.error(f"Error processing page {page_index}: {e}")
                continue
    finally:
        doc.close()

# def rasterize_pdf(
#     pdf_path: str,
#     dpi: int = 200,
#     start_index: int = 0,
#     end_index: int = None,
#     grayscale: bool = True
# ) -> Iterator[dict[int, bytes]]:
#     doc = fitz.open(pdf_path)
#     num_pages = len(doc)

#     if num_pages == 0:
#         raise ValueError("Document has no pages")
#     if start_index < 0:
#         raise ValueError("Start index must be greater than or equal to 0")
#     if end_index is not None and end_index < 0:
#         raise ValueError("End index must be greater than or equal to 0")
#     if end_index is not None and end_index >= num_pages:
#         raise ValueError("End index must be less than the number of pages in the document")

#     try:
#         start = max(0, start_index)
#         stop = min(num_pages - 1, end_index) if end_index is not None else num_pages - 1

#         if start > stop:
#             raise ValueError("Start index must be less than or equal to end index")

#         zoom = dpi / 72
#         mat = fitz.Matrix(zoom, zoom)
#         colorspace = fitz.csGRAY if grayscale else fitz.csRGB

#         for page_index in range(start, stop + 1):
#             try:
#                 page = doc.load_page(page_index)
#                 pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=colorspace)
#                 png_bytes = pix.tobytes("png")

#                 logger.info(
#                     "Rasterized page %d/%d (dpi=%d, size=%dx%d)",
#                     page_index,
#                     num_pages - 1,
#                     dpi,
#                     pix.width,
#                     pix.height
#                 )

#                 yield {"page_index": page_index, "bytes": png_bytes}
#             except Exception as e:
#                 logger.error(f"Error rasterizing page {page_index}: {e}")
#                 continue
#     finally:
#         doc.close()
