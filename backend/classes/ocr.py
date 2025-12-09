from PIL import Image
import pytesseract, logging, io

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

# tesseract = Tesseract()
# test_image = open("test.png", "rb").read()
# print(tesseract.image_to_string(test_image))
