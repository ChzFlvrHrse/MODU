import fitz, logging, dotenv
from typing import Iterator, Optional
from classes.typed_dicts import HybridPage

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFPageConverter:
    """
    Handles converting PDF pages to text/images and uploading them to S3.
    """
    # ---------- Low-level helpers ----------

    def rasterize_page(self, doc: fitz.Document, page_index: int, dpi: int = 200, grayscale: bool = False) -> bytes:
        num_pages = len(doc)

        if num_pages == 0:
            raise ValueError("Document has no pages")

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        colorspace = fitz.csGRAY if grayscale else fitz.csRGB

        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=colorspace)
        png_bytes = pix.tobytes("png")

        logger.info(
            "Rasterized page %d/%d (dpi=%d, size=%dx%d)",
            page_index,
            num_pages - 1,
            dpi,
            pix.width,
            pix.height,
        )
        return png_bytes

    def get_text(self, page: fitz.Page) -> str:
        """Extract plain text from a page."""
        return page.get_text("text").strip()

    def check_pdf_for_images(self, page: fitz.Page) -> bool:
        """Return True if the page has any images."""
        return len(page.get_images(full=True)) > 0

    # ---------- Core generator ----------

    def pdf_page_converter_generator(
        self,
        pdf_path: str,
        dpi: int = 200,
        grayscale: bool = False,
        rasterize_all: bool = False,
        start_index: int = 0,
        end_index: Optional[int] = None,
    ) -> Iterator[HybridPage]:
        """
        Yield HybridPage dicts for the given PDF:
        - Optionally rasterize all pages.
        - Otherwise, only rasterize if the page contains images.
        - Include text if present.
        """

        doc = fitz.open(pdf_path)
        try:
            num_pages = len(doc)

            if num_pages == 0:
                raise ValueError("Document has no pages")
            if start_index < 0:
                raise ValueError(
                    "Start index must be greater than or equal to 0"
                )
            if end_index is not None and end_index < 0:
                raise ValueError(
                    "End index must be greater than or equal to 0"
                )
            if end_index is not None and end_index >= num_pages:
                raise ValueError(
                    "End index must be less than the number of pages in the document"
                )

            start = max(0, start_index)
            stop = (
                min(num_pages - 1, end_index)
                if end_index is not None
                else num_pages - 1
            )

            if start > stop:
                raise ValueError(
                    "Start index must be less than or equal to end index"
                )

            for page_index in range(start, stop + 1):
                try:
                    page = doc.load_page(page_index)

                    # If rasterize_all, immediately yield a raster-only page
                    if rasterize_all:
                        yield {
                            "page_index": page_index,
                            "text": None,
                            "bytes": self.rasterize_page(
                                doc,
                                page_index,
                                dpi=dpi,
                                grayscale=grayscale,
                            ),
                        }

                    text = self.get_text(page)
                    clean_text = text.replace(" ", "").replace("\n", " ")

                    has_text = len(clean_text) > 0
                    has_image = self.check_pdf_for_images(page)

                    logger.info(
                        "Page %d: Text Present: %s, Image Present: %s",
                        page_index,
                        has_text,
                        has_image,
                    )

                    yield {
                        "page_index": page_index,
                        "text": text if has_text else None,
                        "bytes": (
                            self.rasterize_page(
                                doc,
                                page_index,
                                dpi=dpi,
                                grayscale=grayscale,
                            )
                            if has_image
                            else None
                        ),
                    }
                except ValueError as e:
                    logger.error("Error processing page %d: %s", page_index, e)
                    continue
        finally:
            doc.close()
