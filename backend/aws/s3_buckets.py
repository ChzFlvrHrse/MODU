import boto3, os, dotenv, logging
from botocore.config import Config
from classes.typed_dicts import HybridPage

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3Bucket:
    def __init__(self):
        self.bucket_name = os.environ.get("BUCKET_NAME")

    def s3_client(self):
        return boto3.client(
            "s3",
            config=Config(s3={"use_accelerate_endpoint": True}),
            region_name=os.environ.get("AWS_REGION"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )

    def get_objects(self):
        return self.s3_client().list_objects(Bucket=self.bucket_name)['Contents']

    def get_object(self, key: str):
        return self.s3_client().get_object(Bucket=self.bucket_name, Key=key)['Body'].read()

    def upload_page_to_s3(self, page: HybridPage, spec_id: str) -> dict:
        attempts: int = 0
        successes: int = 0

        if page['text']:
            try:
                self.s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/{page['page_index']}.txt",
                    Body=page['text'],
                    ContentType="text/plain",
                    ServerSideEncryption="AES256"
                )

                attempts += 1
                successes += 1
            except Exception as e:
                logger.error(f"Error uploading text. Spec ID: {spec_id}, page {page['page_index']}: {e}")
                attempts += 1

        if page['bytes']:
            try:
                self.s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/{page['page_index']}.png",
                    Body=page['bytes'],
                    ContentType="image/png",
                    ServerSideEncryption="AES256"
                )

                attempts += 1
                successes += 1
            except Exception as e:
                logger.error(f"Error uploading image. Spec ID: {spec_id}, page {page['page_index']}: {e}")
                attempts += 1

        return {
            "page_index": page['page_index'],
            "attempts": attempts,
            "successes": successes
        }

    def delete_object(self, key: str):
        self.s3_client().delete_object(Bucket=self.bucket_name, Key=key)
