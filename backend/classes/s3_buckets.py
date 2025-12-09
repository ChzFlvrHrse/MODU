from itertools import repeat
from botocore.config import Config
from typing import Optional, Iterator
from quart.datastructures import FileStorage
from concurrent.futures import ThreadPoolExecutor
import boto3, os, dotenv, logging, datetime
from classes.pdf_page_converter import PDFPageConverter
from classes.typed_dicts import HybridPage, PdfPageConverterResult

dotenv.load_dotenv()

s3_client = boto3.client(
    "s3",
    config=Config(s3={"use_accelerate_endpoint": True}),
    region_name=os.environ.get("AWS_REGION"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3Bucket:
    def __init__(self):
        self.bucket_name = os.environ.get("BUCKET_NAME")
        self.pdf_page_converter = PDFPageConverter()

    def s3_client(self):
        return s3_client

    def get_objects(self):
        return self.s3_client().list_objects(Bucket=self.bucket_name)['Contents']

    def get_object(self, key: str):
        return self.s3_client().get_object(Bucket=self.bucket_name, Key=key)['Body'].read()

    def upload_page_to_s3(self, page: HybridPage, spec_id: str) -> dict:
        attempts: int = 0
        successes: int = 0
        attempt_page_index = []

        if page['text']:
            try:
                self.s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/converted/{page['page_index']}.txt",
                    Body=page['text'],
                    ContentType="text/plain",
                    ServerSideEncryption="AES256"
                )

                attempts += 1
                successes += 1
            except Exception as e:
                logger.error(f"Error uploading text. Spec ID: {spec_id}, page {page['page_index']}: {e}")
                attempts += 1
                attempt_page_index.append(page['page_index'])

        if page['bytes']:
            try:
                self.s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/converted/{page['page_index']}.png",
                    Body=page['bytes'],
                    ContentType="image/png",
                    ServerSideEncryption="AES256"
                )

                attempts += 1
                successes += 1
            except Exception as e:
                logger.error(f"Error uploading image. Spec ID: {spec_id}, page {page['page_index']}: {e}")
                attempts += 1
                attempt_page_index.append(page['page_index'])

        return {
            "page_index": page['page_index'],
            "attempts": attempts,
            "successes": successes,
            "attempt_page_index": attempt_page_index
        }

    def bulk_upload_to_s3(
        self,
        pdf: bytes,
        spec_id: str,
        max_workers: int = 10,
        dpi: int = 200,
        grayscale: bool = False,
        rasterize_all: bool = False,
        start_index: int = 0,
        end_index: Optional[int] = None,
    ) -> PdfPageConverterResult:
        """
        Convert a PDF into HybridPages and upload each page's
        text/image representation to S3 using a thread pool.
        """

        bucket = self.bucket_name
        logger.info(
            "Uploading PDF to S3 bucket: %s, spec ID: %s",
            bucket,
            spec_id,
        )

        start_time = datetime.datetime.now()
        attempts: int = 0
        successes: int = 0
        last_page_index: Optional[int] = None
        attempt_page_index = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for page_result in executor.map(
                self.upload_page_to_s3,
                self.pdf_page_converter.pdf_page_converter_generator(
                    pdf=pdf,
                    dpi=dpi,
                    grayscale=grayscale,
                    rasterize_all=rasterize_all,
                    start_index=start_index,
                    end_index=end_index,
                ),
                repeat(spec_id)
            ):
                attempts += page_result["attempts"]
                successes += page_result["successes"]
                last_page_index = page_result["page_index"]
                attempt_page_index.extend(page_result["attempt_page_index"])

        end_time = datetime.datetime.now()
        elapsed = end_time - start_time
        success_rate = (successes / attempts * 100) if attempts > 0 else 0.0

        logger.info(
            "Uploaded %d/%d (%.2f%%) pages to S3 bucket: %s, spec ID: %s, "
            "runtime: %s",
            successes,
            attempts,
            success_rate,
            bucket,
            spec_id,
            elapsed,
        )

        logger.info(f"Attempted page indices: {attempt_page_index}")

        return {
            "success_rate": float(success_rate),
            "attempted_uploads": attempts,
            "successful_uploads": successes,
            "unsuccessful_uploads": attempt_page_index if attempt_page_index else "No unsuccessful uploads",
            "runtime": str(elapsed).split(".")[0],
            "bucket": bucket,
            "spec_id": spec_id,
            "dpi": dpi,
            "grayscale": grayscale,
            "rasterize_all": rasterize_all,
            "start_index": start_index,
            "end_index": last_page_index
        }

    def upload_original_pdf(self, file: FileStorage, file_name: str, spec_id: str) -> dict:
        try:
            self.s3_client().put_object(
                Bucket=self.bucket_name,
                # Key=f"{spec_id}/{file_name}/original",
                Key=f"{spec_id}/original",
                Body=file.stream,
                ContentType="application/pdf",
                ServerSideEncryption="AES256"
            )
        except Exception as e:
            logger.error(f"Error uploading original PDF to S3 bucket: {e}")
            return {
                    "message": f"Error uploading original PDF to S3 bucket: {str(e)}",
                    "status_code": 400
            }
        return {
            "message": "Original PDF uploaded to S3 bucket",
            "status_code": 200
        }

    def get_original_pdf(self, spec_id: str) -> dict:
        if not spec_id:
            raise ValueError("Spec ID is required")
        # if file_name is None:
        #     raise ValueError("File name is required")

        try:
            # Get pdf file from S3 bucket
            response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/original")
            return {
                "data": response["Body"].read(),
                "status_code": 200
            }
        except Exception as e:
            logger.error(f"Error getting original PDF from S3 bucket: {e}")
            return {
                "data": f"Error getting original PDF from S3 bucket: {str(e)}",
                "status_code": 400
            }

    def get_converted_pages_generator(self, spec_id: str, start_index: int = 0, end_index: int = 10) -> Iterator[HybridPage]:

        if not end_index:
            end_index = 10
        if start_index < 0:
            raise ValueError("Start index must be greater than or equal to 0")
        if end_index < 0:
            raise ValueError("End index must be greater than or equal to 0")
        if end_index < start_index:
            raise ValueError("End index must be greater than or equal to start index")
        # if end_index is not None and end_index >= 10:
        #     raise ValueError("End index must be less than 10")

        if start_index == end_index:
            end_index = start_index + 1

        # converted_pages = []

        try:
            for i in range(start_index, end_index + 1):
                try:
                    tex_response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{i}.txt")
                    if tex_response:
                        text = tex_response["Body"].read().decode("utf-8")
                    else:
                        logger.debug(f"No text for page {i}")
                        text = None
                except Exception as e:
                    logger.debug(f"No text for page {i}: {e}")
                    text = None

                try:
                    bytes_response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{i}.png")
                    if bytes_response:
                        bytes = bytes_response["Body"].read()
                    else:
                        logger.debug(f"No image for page {i}")
                        bytes = None
                except Exception as e:
                    logger.debug(f"No image for page {i}: {e}")
                    bytes = None

                yield {
                    "page_index": i,
                    "text": text,
                    "bytes": bytes
                }
        except Exception as e:
            logger.error(f"Error getting converted pages from S3 bucket: {e}")
            raise ValueError(f"Error getting converted pages from S3 bucket: {str(e)}")

    def delete_object(self, key: str):
        self.s3_client().delete_object(Bucket=self.bucket_name, Key=key)

# if __name__ == "__main__":
#     s3 = S3Bucket()
#     spec_id = "2ad9cd93-2a40-4b3e-a11c-e52decfe0e6c"
#     converted_pages = s3.get_converted_pages_generator(spec_id, start_index=0, end_index=10)
#     for page in converted_pages:
#         print(page)
