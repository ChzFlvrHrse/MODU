from PIL import Image
import pytesseract, logging, io, fitz, re, dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Tesseract:

    def __init__(self, lang: str = "eng", oem: int = 3, psm: int = 3, extra_config: str = ""):
        """
        - lang: Tesseract language code ("eng", "eng+deu", etc.)
        - oem: OCR Engine Mode (3 = default, best)
        - psm: Page Segmentation Mode (6 = block of text, 7 = single line, etc.)
        - extra_config: free-form string to append to config (e.g. "--psm 6")
        """
        self.lang: str = lang
        self.config: str = f"--oem {oem} --psm {psm} {extra_config}".strip()

    def image_to_string(self, image: bytes) -> str:
        """
        Extracts text from an image.
        """
        try:
            with Image.open(io.BytesIO(image)) as img:
                text = pytesseract.image_to_string(
                    img,
                    config=self.config,
                    lang=self.lang
                )
            return text
        except Exception as e:
            logger.error(f"Error converting image to string: {e}")
            return ""

    def image_to_data(self, image: bytes) -> dict:
        """
        Returns detailed per-word boxes/confidence
        """
        try:
            with Image.open(io.BytesIO(image)) as img:
                data = pytesseract.image_to_data(
                    img,
                    config=self.config,
                    lang=self.lang
                )
            return data
        except Exception as e:
            logger.error(f"Error converting image to data: {e}")
            return {}

class OCRQualityChecker(Tesseract):
    """
    Handles OCR quality checking with retry at higher DPI levels.
    """
    def _text_quality_metrics(self, text: str) -> tuple[int, int]:
        clean_text = text.replace(" ", "").replace("\n", " ")
        alnum = sum(c.isalnum() for c in clean_text)
        word_count = len(re.findall(r"[A-Za-z0-9]{2,}", text))
        return alnum, word_count

    def _passes_quality(self, alnum: int, word_count: int) -> bool:
        return (alnum >= 50 and word_count >= 10) or (word_count >= 15)

    def ocr_quality_assurance(
        self,
        page: fitz.Page,
        page_index: int,
        total_pages: int,
        dpi_start: int = 200,
        grayscale: bool = False,
        dpi_steps: tuple[int, ...] = (200, 250, 300),
    ) -> dict:
        """
        Try OCR at increasing DPI levels until quality passes.
        Returns dict with: passes, alnum, word_count, text, dpi_used
        """
        best: dict | None = None

        for dpi in dpi_steps:
            rasterized_bytes = self.rasterize_page(
                page,
                total_pages,
                page_index,
                dpi=dpi,
                grayscale=grayscale,
            )
            text = self.image_to_string(rasterized_bytes) or ""
            alnum, word_count = self._text_quality_metrics(text)
            passes = self._passes_quality(alnum, word_count)

            result = {
                "passes": passes,
                "alnum": alnum,
                "word_count": word_count,
                "text": text,
                "dpi_used": dpi
            }

            # Keep best result even if it doesn't pass
            if best is None or (result["word_count"], result["alnum"]) > (best["word_count"], best["alnum"]):
                logger.info(f"Best result: {result} for page {page_index} at dpi {dpi}")
                best = result

            if passes:
                logger.info(f"Passes quality assurance for page {page_index} at dpi {dpi}")
                return result

        return best or {"passes": False, "alnum": 0, "word_count": 0, "text": "", "dpi_used": dpi_start}
