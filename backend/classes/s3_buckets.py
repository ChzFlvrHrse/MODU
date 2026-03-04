from botocore.config import Config
from quart.datastructures import FileStorage
from typing import Optional, AsyncGenerator
from classes.pdf_page_converter import PDFPageConverter
from classes.typed_dicts import HybridPage, PdfPageConverterResult
import aioboto3
import os
import dotenv
import logging
import datetime
import fitz
import asyncio
import threading
import base64
import io
from PIL import Image

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Bucket(PDFPageConverter):
    def __init__(self):
        super().__init__()
        self.bucket_name = os.environ.get("BUCKET_NAME")
        self._session = aioboto3.Session()

    def s3_client(self):
        return self._session.client(
            "s3",
            config=Config(s3={"use_accelerate_endpoint": True}),
            region_name=os.environ.get("AWS_REGION"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )

    # ---------- Generic low-level helpers ----------

    async def put_object_with_client(
        self,
        key: str,
        body: bytes,
        content_type: str,
        s3_client: any
    ) -> dict:
        try:
            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type,
                ServerSideEncryption="AES256"
            )
            return {"s3_key": key, "status_code": 200}
        except Exception as e:
            logger.error(f"Error uploading object {key}: {e}")
            return {"message": str(e), "status_code": 400}

    async def delete_object_with_client(
        self,
        key: str,
        s3_client: any
    ) -> dict:
        try:
            await s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return {"status_code": 200}
        except Exception as e:
            logger.error(f"Error deleting object {key}: {e}")
            return {"message": str(e), "status_code": 400}

    # ---------- Image compression ----------

    MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB to stay safely under 5MB limit

    def compress_image(self, image_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> tuple[bytes, str]:
        """Compress image to stay under max_bytes. Returns (bytes, media_type)."""
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        for quality in [85, 70, 50, 30]:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            compressed = buffer.getvalue()
            if len(compressed) <= max_bytes:
                return base64.b64encode(compressed).decode("utf-8"), "image/jpeg"

        while True:
            img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=50, optimize=True)
            compressed = buffer.getvalue()
            if len(compressed) <= max_bytes or img.width < 100:
                return base64.b64encode(compressed).decode("utf-8"), "image/jpeg"

    # ---------- Page retrieval ----------

    async def get_object_with_client(self, key: str, s3_client: any):
        response = await s3_client.get_object(Bucket=self.bucket_name, Key=key)
        body = response["Body"]
        data = await body.read()
        body.close()
        return data

    async def get_text_page_with_client(
        self,
        spec_id: str,
        index: int,
        s3_client: any,
        prefix: str = '/converted'
    ):
        key = f"{spec_id}{prefix}/{index}/TEXT.txt"
        try:
            text = await self.get_object_with_client(key, s3_client)
            logger.info(f"Text page {index} found")
            return {"text": text.decode("utf-8", errors="replace"), "page_index": index}
        except Exception as e:
            logger.warning(f"Error getting text page {index}: {e}")
            return {"text": None, "page_index": index}

    async def get_image_page_with_client(
        self,
        spec_id: str,
        index: int,
        s3_client: any,
        prefix: str = '/converted'
    ):
        key = f"{spec_id}{prefix}/{index}/IMAGE.png"
        try:
            image_bytes = await self.get_object_with_client(key, s3_client)
            compressed, media_type = self.compress_image(image_bytes)
            return {"bytes": compressed, "media_type": media_type, "page_index": index}
        except Exception as e:
            logger.warning(f"Error getting image page {index}: {e}")
            return {"bytes": None, "media_type": None, "page_index": index}

    async def get_single_page_with_client(
        self,
        spec_id: str,
        page_index: int,
        s3_client: any,
        prefix: str = '/converted'
    ) -> HybridPage:
        if page_index < 0:
            raise ValueError("Page index must be greater than or equal to 0")

        spec_check = await self.get_original_pdf_with_client(spec_id, s3_client)
        if spec_check["status_code"] != 200:
            raise ValueError(spec_check["data"])

        text_result, image_result = await asyncio.gather(
            self.get_text_page_with_client(spec_id, page_index, s3_client, prefix),
            self.get_image_page_with_client(spec_id, page_index, s3_client, prefix)
        )

        return {
            "page_index": page_index,
            "text": text_result["text"],
            "bytes": image_result["bytes"]
        }

    async def get_converted_pages_generator_with_client(
        self,
        spec_id: str,
        s3_client: any,
        start_index: int = 0,
        end_index: int = 10,
        prefix: str = '/converted'
    ) -> AsyncGenerator[HybridPage, None]:
        if start_index < 0:
            raise ValueError("Start index must be greater than or equal to 0")
        if end_index < 0:
            raise ValueError("End index must be greater than or equal to 0")
        if end_index < start_index:
            raise ValueError("End index must be greater than or equal to start index")

        for i in range(start_index, end_index):
            text, bytes_data = await asyncio.gather(
                self.get_text_page_with_client(spec_id, i, s3_client, prefix),
                self.get_image_page_with_client(spec_id, i, s3_client, prefix)
            )

            yield {
                "page_index": i,
                "text": text["text"],
                "bytes": bytes_data["bytes"],
                "media_type": bytes_data["media_type"]
            }

    # ---------- Original PDF ----------

    async def upload_original_pdf_with_client(self, files: list[FileStorage], spec_id: str, s3: any) -> dict:
        successes: int = 0
        for i, file in enumerate(files):
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/original/{i+1}",
                    Body=file.stream,
                    ContentType=file.content_type,
                    ServerSideEncryption="AES256"
                )
                logger.info(f"Uploaded original PDF {i+1} to S3 bucket")
                successes += 1
            except Exception as e:
                logger.error(f"Error uploading original PDF {i+1} to S3 bucket: {e}")
                return {
                    "message": f"Error uploading original PDF {i+1} to S3 bucket: {str(e)}",
                    "status_code": 400
                }
        return {
            "message": f"{successes}/{len(files)} original PDFs uploaded to S3 bucket",
            "spec_id": spec_id,
            "status_code": 200
        }

    async def get_original_pdf_with_client(self, spec_id: str, s3_client: any) -> dict:
        if not spec_id:
            raise ValueError("Spec ID is required")

        try:
            response = await s3_client.list_objects(Bucket=self.bucket_name, Prefix=f"{spec_id}/original/")
            contents = sorted(response.get("Contents", []), key=lambda x: x["Key"])

            if not contents:
                return {"data": "No original PDFs found", "status_code": 404}

            if len(contents) == 1:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=contents[0]["Key"])
                pdf_bytes = await response["Body"].read()
                return {"data": pdf_bytes, "status_code": 200}

            merged_doc = fitz.open()
            for item in contents:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=item["Key"])
                pdf_bytes = await response["Body"].read()
                src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                merged_doc.insert_pdf(src_doc)
                src_doc.close()

            merged_bytes = merged_doc.tobytes()
            merged_doc.close()

            return {"data": merged_bytes, "status_code": 200}
        except Exception as e:
            logger.error(f"Error getting original PDF from S3 bucket: {e}")
            return {"data": f"Error getting original PDF from S3 bucket: {str(e)}", "status_code": 400}

    async def get_original_page_count_with_client(
        self,
        spec_id: str,
        s3_client: any,
        prefix: str = 'original_pages'
    ) -> int:
        paginator = s3_client.get_paginator("list_objects_v2")
        response = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=f"{spec_id}/{prefix}/",
        )
        count = 0
        async for page in response:
            count += len(page.get("Contents", []))
        return count

    async def upload_original_pdf_pages(self, pdf: bytes, spec_id: str, s3_client) -> dict:
        src = fitz.open(stream=pdf, filetype="pdf")
        total_pages = src.page_count

        async def upload_page(page_index: int):
            doc = fitz.open()
            doc.insert_pdf(src, from_page=page_index, to_page=page_index)
            page_bytes = doc.tobytes()
            doc.close()

            key = f"{spec_id}/original_pages/page_{page_index:04d}.pdf"
            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=page_bytes,
                ContentType="application/pdf"
            )
            logger.info(f"Uploaded original PDF page {page_index} to S3 bucket")

        await asyncio.gather(*[upload_page(page_index) for page_index in range(total_pages)])

        src.close()
        return {"total_pages": total_pages, "status_code": 200}

    # ---------- Page uploads ----------

    async def upload_page_to_s3_with_client(
        self,
        page: HybridPage,
        spec_id: str,
        s3: any,
        prefix: str = '/converted'
    ) -> dict:
        attempts: int = 0
        successes: int = 0
        attempt_page_index = []

        if page['text']:
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}{prefix}/{page['page_index']}/TEXT.txt",
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
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}{prefix}/{page['page_index']}/IMAGE.png",
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

    async def bulk_upload_to_s3_with_client(
        self,
        pdf: bytes,
        spec_id: str,
        s3_client: any,
        max_workers: int = 10,
        dpi_override: Optional[int] = None,
        grayscale: bool = False,
        rasterize_all: bool = False,
        start_index: int = 0,
        end_index: Optional[int] = None,
        prefix: str = '/converted',
    ) -> PdfPageConverterResult:
        try:
            start_time = datetime.datetime.now()
            bucket = self.bucket_name
            logger.info(
                "Uploading PDF to S3 bucket: %s, spec ID: %s, start time: %s",
                bucket, spec_id, start_time,
            )

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue(maxsize=max_workers * 2)
            STOP = object()

            def producer():
                try:
                    for page in self.pdf_page_converter_generator(
                        pdf=pdf,
                        dpi_override=dpi_override,
                        grayscale=grayscale,
                        rasterize_all=rasterize_all,
                        start_index=start_index,
                        end_index=end_index,
                    ):
                        asyncio.run_coroutine_threadsafe(queue.put(page), loop).result()
                finally:
                    for _ in range(max_workers):
                        asyncio.run_coroutine_threadsafe(queue.put(STOP), loop).result()
                    logger.info("Producer finished")

            threading.Thread(target=producer, daemon=True).start()

            attempts: int = 0
            successes: int = 0
            attempt_page_index = []
            indexes_with_no_text_or_image: list[int] = []

            async def consumer():
                nonlocal attempts, successes, attempt_page_index, indexes_with_no_text_or_image
                while True:
                    try:
                        item = await queue.get()
                        if item is STOP:
                            break
                        page_result = await asyncio.wait_for(
                            self.upload_page_to_s3_with_client(item, spec_id, s3_client, prefix),
                            timeout=60
                        )
                        attempts += page_result["attempts"]
                        successes += page_result["successes"]
                        attempt_page_index.extend(page_result["attempt_page_index"])
                        if page_result["attempts"] == 0:
                            indexes_with_no_text_or_image.append(page_result["page_index"])
                    except Exception as e:
                        logger.error(f"Error uploading page to S3 bucket: {e}")
                        continue
                    finally:
                        queue.task_done()

            await asyncio.gather(*(consumer() for _ in range(max_workers)))

            end_time = datetime.datetime.now()
            elapsed = end_time - start_time
            success_rate = (successes / attempts * 100) if attempts > 0 else 0.0

            logger.info(
                "Uploaded %d/%d (%.2f%%) pages to S3 bucket: %s, spec ID: %s, runtime: %s",
                successes, attempts, success_rate, bucket, spec_id, elapsed,
            )

            return {
                "success_rate": float(success_rate),
                "attempted_uploads": attempts,
                "successful_uploads": successes,
                "unsuccessful_uploads": attempt_page_index if attempt_page_index else "No unsuccessful uploads",
                "runtime": str(elapsed).split(".")[0],
                "spec_id": spec_id,
                "dpi_override": dpi_override,
                "grayscale": grayscale,
                "rasterize_all": rasterize_all,
                "start_index": start_index,
                "end_index": end_index,
                "indexes_with_no_text_or_image": indexes_with_no_text_or_image,
                "total_indexes_with_no_text_or_image": len(indexes_with_no_text_or_image),
                "status_code": 200
            }
        except Exception as e:
            logger.error(f"Error uploading PDF to S3 bucket: {e}")
            return {"message": f"Error uploading PDF to S3 bucket: {str(e)}", "status_code": 400}

    # ---------- Submittal uploads ----------

    async def upload_submittal_with_client(
        self,
        file: FileStorage,
        spec_id: str,
        package_id: int,
        submittal_id: int,
        s3_client: any
    ) -> dict:
        key = f"{spec_id}/submittals/{package_id}/{submittal_id}/{file.filename}"
        return await self.put_object_with_client(
            key=key,
            body=file.stream,
            content_type=file.content_type,
            s3_client=s3_client
        )

    async def get_submittal_with_client(
        self,
        s3_key: str,
        s3_client: any
    ) -> dict:
        try:
            data = await self.get_object_with_client(s3_key, s3_client)
            return {"data": data, "status_code": 200}
        except Exception as e:
            logger.error(f"Error getting submittal {s3_key}: {e}")
            return {"data": str(e), "status_code": 400}

    async def delete_submittal_with_client(
        self,
        s3_key: str,
        s3_client: any
    ) -> dict:
        return await self.delete_object_with_client(s3_key, s3_client)

    # ---------- Existence checks ----------

    async def check_pdf_exists_with_client(self, spec_id: str, s3_client: any) -> bool:
        resp = await s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=f"{spec_id}/original/",
            MaxKeys=1
        )
        return resp.get("KeyCount", 0) > 0

    # ---------- S3 object listing ----------

    async def get_objects_gen_with_client(self, s3_client: any, prefix: str = "") -> AsyncGenerator[list[dict], None]:
        paginator = s3_client.get_paginator("list_objects_v2")
        kwargs = {"Bucket": self.bucket_name}
        if prefix:
            kwargs["Prefix"] = prefix
        async for page in paginator.paginate(**kwargs):
            if "Contents" in page:
                yield page.get("Contents", [])

    # ---------- Utilities ----------

    def group_contiguous_pages(self, pages: list[int]) -> tuple[list[list[int]], bool]:
        if not pages:
            return [], True

        sorted_pages = sorted(pages)
        groups = []
        current_group = [sorted_pages[0]]
        all_contiguous = True

        for page in sorted_pages[1:]:
            if page == current_group[-1] + 1:
                current_group.append(page)
            else:
                all_contiguous = False
                groups.append(current_group)
                current_group = [page]
        groups.append(current_group)

        return groups, all_contiguous
