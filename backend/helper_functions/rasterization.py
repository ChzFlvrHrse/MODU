import fitz, logging, boto3, os, dotenv
from typing import Iterator, Optional, TypedDict

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AWS_REGION")
)

bucket = os.environ.get("BUCKET_NAME")

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

def get_text(page: fitz.Page) -> str:
    return page.get_text("text").strip()

def check_pdf_for_images(page: fitz.Page) -> bool:
    return len(page.get_images(full=True)) > 0

def hybrid_pdf(
    pdf_path: str,
    dpi: int = 200,
    grayscale: bool = True,
    rasterize_all: bool = False,
    start_index: int = 0,
    end_index: int = None
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
                page = doc.load_page(page_index)

                if rasterize_all:
                    yield{
                        "page_index": page_index,
                        "text": None,
                        "bytes": rasterize_page(doc, page_index, dpi, grayscale=grayscale)
                    }

                text = get_text(page)
                clean_text = text.replace(" ", "").replace("\n", " ")

                has_text = len(clean_text) > 0
                has_image = check_pdf_for_images(page)

                logger.info("Page %d: Text Present: %s, Image Present: %s", page_index, has_text, has_image)

                yield{
                    "page_index": page_index,
                    "text": text if has_text else None,
                    "bytes": rasterize_page(doc, page_index, dpi, grayscale=grayscale) if has_image else None
                }
            except ValueError as e:
                logger.error(f"Error processing page {page_index}: {e}")
                continue
    finally:
        doc.close()

def pdf_to_s3_bucket(
    pdf_path: str,
    bucket: str,
    spec_id: str,
    dpi: int = 200,
    grayscale: bool = True,
    rasterize_all: bool = False,
    start_index: int = 0,
    end_index: int = None
) -> None:
    for page in hybrid_pdf(pdf_path, dpi, grayscale, rasterize_all, start_index, end_index):
        if page['text']:
            s3.put_object(
                Bucket=bucket,
                Key=f"{spec_id}/page_{page['page_index']}.txt",
                Body=page['text']
            )
        if page['bytes']:
            s3.put_object(
                Bucket=bucket,
                Key=f"{spec_id}/page_{page['page_index']}.png",
                Body=page['bytes']
            )
    return None
