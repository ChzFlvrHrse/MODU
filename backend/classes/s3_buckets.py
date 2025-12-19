from itertools import repeat
from botocore.config import Config
from quart.datastructures import FileStorage
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Iterator, AsyncGenerator
from classes.pdf_page_converter import PDFPageConverter
from classes.typed_dicts import HybridPage, PdfPageConverterResult
import aioboto3, os, dotenv, logging, datetime, fitz, asyncio, threading

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3Bucket(PDFPageConverter):
    def __init__(self):
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

    async def get_object(self, key: str):
        async with self.s3_client() as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key)
            body = response["Body"]
            data = await body.read()
            body.close()
            return data

    async def get_object_with_client(self, key: str, s3: any):
        response = await s3.get_object(Bucket=self.bucket_name, Key=key)
        body = response["Body"]
        data = await body.read()
        body.close()
        return data

    async def get_text_page(self, spec_id: str, index: int):
        key = f"{spec_id}/converted/{index}/TEXT.txt"
        try:
            text = await self.get_object(key)
            return {"text": text.decode("utf-8", errors="replace"), "page_index": index}
        except Exception as e:
            logger.error(f"Error getting text page {index}: {e}")
            return {"text": None, "page_index": index}

    async def get_image_page(self, spec_id: str, index: int):
        key = f"{spec_id}/converted/{index}/IMAGE.png"
        try:
            image = await self.get_object(key)
            return fitz.open(stream=image, filetype="png")
        except Exception as e:
            logger.error(f"Error getting image page {index}: {e}")
            return {"bytes": None, "page_index": index}

    async def get_text_page_with_client(self, spec_id: str, index: int, s3_client: any):
        key = f"{spec_id}/converted/{index}/TEXT.txt"
        try:
            text = await self.get_object_with_client(key, s3_client)
            logger.info(f"Text page {index} found")
            return {"text": text.decode("utf-8", errors="replace"), "page_index": index}
        except Exception as e:
            logger.error(f"Error getting text page {index}: {e}")
            return {"text": None, "page_index": index}

    async def get_image_page_with_client(self, spec_id: str, index: int, s3_client: any):
        key = f"{spec_id}/converted/{index}/IMAGE.png"
        try:
            image = await self.get_object_with_client(key, s3_client)
            logger.info(f"Image page {index} found")
            return {"bytes": fitz.open(stream=image, filetype="png"), "page_index": index} if image else None
        except Exception as e:
            logger.error(f"Error getting image page {index}: {e}")
            return {"bytes": None, "page_index": index}

    async def get_objects_gen(self, prefix: str = "") -> AsyncGenerator[list[dict], None]:
        async with self.s3_client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            kwargs = {"Bucket": self.bucket_name}
            if prefix:
                kwargs["Prefix"] = prefix
            async for page in paginator.paginate(**kwargs):
                if "Contents" in page:
                    yield page.get("Contents", [])

    async def get_objects_gen_with_client(self, s3_client: any, prefix: str = "") -> AsyncGenerator[list[dict], None]:
        paginator = s3_client.get_paginator("list_objects_v2")
        kwargs = {"Bucket": self.bucket_name}
        if prefix:
            kwargs["Prefix"] = prefix
        async for page in paginator.paginate(**kwargs):
            if "Contents" in page:
                yield page.get("Contents", [])

    async def upload_page_to_s3(self, page: HybridPage, spec_id: str) -> dict:
        attempts: int = 0
        successes: int = 0
        attempt_page_index = []

        if page['text']:
            try:
                await self.s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/converted/{page['page_index']}/TEXT.txt",
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
                await self.s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/converted/{page['page_index']}/IMAGE.png",
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

    async def upload_page_to_s3_with_client(self, page: HybridPage, spec_id: str, s3: any) -> dict:
        attempts: int = 0
        successes: int = 0
        attempt_page_index = []

        if page['text']:
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=f"{spec_id}/converted/{page['page_index']}/TEXT.txt",
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
                    Key=f"{spec_id}/converted/{page['page_index']}/IMAGE.png",
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

    async def bulk_upload_to_s3(
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
        try:
            bucket = self.bucket_name
            logger.info(
                "Uploading PDF to S3 bucket: %s, spec ID: %s",
                bucket,
                spec_id,
            )

            start_time = datetime.datetime.now()
            last_page_index: int = 0
            attempts: int = 0
            successes: int = 0
            attempt_page_index = []
            indexes_with_no_text_or_image: list[int] = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for page_result in executor.map(
                    await self.upload_page_to_s3,
                    await asyncio.to_thread(self.pdf_page_converter_generator,
                        pdf=pdf,
                        dpi=dpi,
                        grayscale=grayscale,
                        rasterize_all=rasterize_all,
                        start_index=start_index,
                        end_index=end_index,
                    ),
                    repeat(spec_id)):
                        attempts += page_result["attempts"]
                        successes += page_result["successes"]
                        last_page_index = page_result["page_index"]
                        attempt_page_index.extend(page_result["attempt_page_index"])

                        if page_result["attempts"] == 0:
                            indexes_with_no_text_or_image.append(page_result["page_index"])

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
                "end_index": end_index,
                "indexes_with_no_text_or_image": indexes_with_no_text_or_image,
                "total_indexes_with_no_text_or_image": len(indexes_with_no_text_or_image),
                "status_code": 200
            }
        except Exception as e:
            logger.error(f"Error uploading PDF to S3 bucket: {e}")
            return { "message": f"Error uploading PDF to S3 bucket: {str(e)}", "status_code": 400 }

    async def bulk_upload_to_s3_with_client(
        self,
        pdf: bytes,
        spec_id: str,
        s3_client: any,
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
        try:
            start_time = datetime.datetime.now()
            bucket = self.bucket_name
            logger.info(
                "Uploading PDF to S3 bucket: %s, spec ID: %s, start time: %s",
                bucket,
                spec_id,
                start_time,
            )

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue(maxsize=max_workers * 2)
            STOP = object()

            def producer():
                try:
                    for page in self.pdf_page_converter_generator(
                        pdf=pdf,
                        dpi=dpi,
                        grayscale=grayscale,
                        rasterize_all=rasterize_all,
                        start_index=start_index,
                        end_index=end_index,
                    ):
                        asyncio.run_coroutine_threadsafe(queue.put(page), loop).result()
                finally:
                    for _ in range(max_workers):
                        asyncio.run_coroutine_threadsafe(queue.put(STOP), loop).result()
                    logger.info(f"Producer finished")

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
                        page_result = await asyncio.wait_for(self.upload_page_to_s3_with_client(item, spec_id, s3_client), timeout=60)
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
                "Uploaded %d/%d (%.2f%%) pages to S3 bucket: %s, spec ID: %s, "
                "runtime: %s",
                successes,
                attempts,
                success_rate,
                bucket,
                spec_id,
                elapsed,
            )

            return {
                "success_rate": float(success_rate),
                "attempted_uploads": attempts,
                "successful_uploads": successes,
                "unsuccessful_uploads": attempt_page_index if attempt_page_index else "No unsuccessful uploads",
                "runtime": str(elapsed).split(".")[0],
                "spec_id": spec_id,
                "dpi": dpi,
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
            return { "message": f"Error uploading PDF to S3 bucket: {str(e)}", "status_code": 400 }

    async def upload_original_pdf(self, files: list[FileStorage], spec_id: str) -> dict:
        successes: int = 0
        for i, file in enumerate(files):
            try:
                self.s3_client().put_object(
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

    async def get_original_pdf(self, spec_id: str) -> dict:
        if not spec_id:
            raise ValueError("Spec ID is required")

        try:
            # Get pdf file from S3 bucket
            response = self.s3_client().list_objects(Bucket=self.bucket_name, Prefix=f"{spec_id}/original/")

            # Sort by key to maintain order (1, 2, 3, etc.)
            contents = sorted(response.get("Contents", []), key=lambda x: x["Key"])

            if not contents:
                return {
                    "data": "No original PDFs found",
                    "status_code": 404
                }

            # If only one PDF, return it directly
            if len(contents) == 1:
                pdf_bytes = self.s3_client().get_object(Bucket=self.bucket_name, Key=contents[0]["Key"])["Body"].read()
                return {
                    "data": pdf_bytes,
                    "status_code": 200
                }

            # Merge multiple PDFs using PyMuPDF
            merged_doc = fitz.open()
            for item in contents:
                pdf_bytes = self.s3_client().get_object(Bucket=self.bucket_name, Key=item["Key"])["Body"].read()
                src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                merged_doc.insert_pdf(src_doc)
                src_doc.close()

            merged_bytes = merged_doc.tobytes()
            merged_doc.close()

            return {
                "data": merged_bytes,
                "status_code": 200
            }
        except Exception as e:
            logger.error(f"Error getting original PDF from S3 bucket: {e}")
            return {
                "data": f"Error getting original PDF from S3 bucket: {str(e)}",
                "status_code": 400
            }

    async def get_original_pdf_with_client(self, spec_id: str, s3_client: any) -> dict:
        if not spec_id:
            raise ValueError("Spec ID is required")

        try:
            # Get pdf file from S3 bucket
            response = await s3_client.list_objects(Bucket=self.bucket_name, Prefix=f"{spec_id}/original/")

            # Sort by key to maintain order (1, 2, 3, etc.)
            contents = sorted(response.get("Contents", []), key=lambda x: x["Key"])

            if not contents:
                return {
                    "data": "No original PDFs found",
                    "status_code": 404
                }

            # If only one PDF, return it directly
            if len(contents) == 1:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=contents[0]["Key"])
                pdf_bytes = await response["Body"].read()
                return {
                    "data": pdf_bytes,
                    "status_code": 200
                }

            # Merge multiple PDFs using PyMuPDF
            merged_doc = fitz.open()
            for item in contents:
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=item["Key"])
                pdf_bytes = await response["Body"].read()
                src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                merged_doc.insert_pdf(src_doc)
                src_doc.close()

            merged_bytes = merged_doc.tobytes()
            merged_doc.close()

            return {
                "data": merged_bytes,
                "status_code": 200
            }
        except Exception as e:
            logger.error(f"Error getting original PDF from S3 bucket: {e}")
            return {
                "data": f"Error getting original PDF from S3 bucket: {str(e)}",
                "status_code": 400
            }

    async def get_original_page_count(self, spec_id: str) -> int:
        paginator = self.s3_client().get_paginator("list_objects_v2")
        response = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=f"{spec_id}/converted/",
            Delimiter="/"
        )
        count = 0
        async for page in response:
            count += len(page.get("CommonPrefixes", []))
        return count

    async def get_original_page_count_with_client(self, spec_id: str, s3_client: any) -> int:
        """Get the number of pages in the original PDF."""
        paginator = s3_client.get_paginator("list_objects_v2")
        response = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=f"{spec_id}/converted/",
            Delimiter="/"
        )
        count = 0
        async for page in response:
            count += len(page.get("CommonPrefixes", []))
        return count

    async def get_converted_pages_generator(self, spec_id: str, start_index: int = 0, end_index: int = 10) -> AsyncGenerator[HybridPage, None]:

        if start_index < 0:
            raise ValueError("Start index must be greater than or equal to 0")
        if end_index < 0:
            raise ValueError("End index must be greater than or equal to 0")
        if end_index < start_index:
            raise ValueError("End index must be greater than or equal to start index")

        if start_index == end_index:
            end_index = start_index + 1

        try:
            for i in range(start_index, end_index+1):
                try:
                    text_response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{i}.txt")
                    if text_response:
                        text = text_response["Body"].read().decode("utf-8")
                    else:
                        logger.debug(f"No text for page {i}")
                        text = None
                except Exception as e:
                    logger.debug(f"No text for page {i}: {e}")
                    text = None

                try:
                    bytes_response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{i}.png")
                    if bytes_response:
                        bytes_data = bytes_response["Body"].read()
                    else:
                        logger.debug(f"No image for page {i}")
                        bytes_data = None
                except Exception as e:
                    logger.debug(f"No image for page {i}: {e}")
                    bytes_data = None

                yield {
                    "page_index": i,
                    "text": text,
                    "bytes": bytes_data
                }
        except Exception as e:
            logger.error(f"Error getting converted pages from S3 bucket: {e}")
            raise ValueError(f"Error getting converted pages from S3 bucket: {str(e)}")

    async def get_converted_pages_generator_with_client(self, spec_id: str, s3_client: any, start_index: int = 0, end_index: int = 10) -> AsyncGenerator[HybridPage, None]:

        if start_index < 0:
            raise ValueError("Start index must be greater than or equal to 0")
        if end_index < 0:
            raise ValueError("End index must be greater than or equal to 0")
        if end_index < start_index:
            raise ValueError("End index must be greater than or equal to start index")

        for i in range(start_index, end_index):
            text, bytes_data = await asyncio.gather(
                self.get_text_page_with_client(spec_id, i, s3_client),
                self.get_image_page_with_client(spec_id, i, s3_client)
            )

            yield {
                "page_index": i,
                "text": text["text"],
                "bytes": bytes_data["bytes"]
            }

    async def get_single_page(self, spec_id: str, page_index: int) -> HybridPage:
        if page_index < 0:
            raise ValueError("Page index must be greater than or equal to 0")
        if page_index >= self.get_converted_page_count(spec_id):
            raise ValueError(f"Page index {page_index} is greater than the number of converted pages: {self.get_converted_page_count(spec_id)}")

        spec_check = self.get_original_pdf(spec_id)
        if spec_check["status_code"] != 200:
            raise ValueError(spec_check["data"])

        try:
            tex_response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{page_index}.txt")
            if tex_response:
                text = tex_response["Body"].read().decode("utf-8")
            else:
                logger.debug(f"No text for page {page_index}")
                text = None
        except Exception as e:
            logger.debug(f"No text for page {page_index}: {e}")
            text = None

        try:
            bytes_response = self.s3_client().get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{page_index}.png")
            if bytes_response:
                bytes = bytes_response["Body"].read()
            else:
                logger.debug(f"No image for page {page_index}")
                bytes = None
        except Exception as e:
            logger.debug(f"No image for page {page_index}: {e}")
            bytes = None

        return {
            "page_index": page_index,
            "text": text,
            "bytes": bytes
        }

    async def get_single_page_with_client(self, spec_id: str, page_index: int, s3_client: any) -> HybridPage:
        if page_index < 0:
            raise ValueError("Page index must be greater than or equal to 0")
        # if page_index >= await self.get_converted_page_count_with_client(spec_id, s3_client):
        #     raise ValueError(f"Page index {page_index} is greater than the number of converted pages: {await s3.get_converted_page_count_with_client(spec_id, s3)}")

        spec_check = await self.get_original_pdf_with_client(spec_id, s3_client)
        if spec_check["status_code"] != 200:
            raise ValueError(spec_check["data"])

        try:
            tex_response = await s3_client.get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{page_index}.txt")
            if tex_response:
                text = tex_response["Body"].read().decode("utf-8")
            else:
                logger.debug(f"No text for page {page_index}")
                text = None
        except Exception as e:
            logger.debug(f"No text for page {page_index}: {e}")
            text = None

        try:
            bytes_response = await s3_client.get_object(Bucket=self.bucket_name, Key=f"{spec_id}/converted/{page_index}.png")
            if bytes_response:
                bytes = bytes_response["Body"].read()
            else:
                logger.debug(f"No image for page {page_index}")
                bytes = None
        except Exception as e:
            logger.debug(f"No image for page {page_index}: {e}")
            bytes = None

        return {
            "page_index": page_index,
            "text": text,
            "bytes": bytes
        }

    async def check_pdf_exists(self, spec_id: str) -> bool:
        async with self.s3_client() as s3:
            resp = await s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{spec_id}/original/",
                MaxKeys=1,
            )
            return resp.get("KeyCount", 0) > 0

    async def check_pdf_exists_with_client(self, spec_id: str, s3_client: any) -> bool:
        resp = await s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=f"{spec_id}/original/",
            MaxKeys=1
        )
        return resp.get("KeyCount", 0) > 0

    async def delete_object(self, key: str):
        await self.s3_client().delete_object(Bucket=self.bucket_name, Key=key)

# if __name__ == "__main__":
#     async def main():
#         s3 = S3Bucket()
#         spec_id = "1ca7077a-ac58-4f5a-9b40-f6847ff235e2"
#         index = 0
#         async with s3.s3_client() as s3_client:
#             get_object = await s3.get_text_page_with_client(spec_id, index, s3_client)
#             print(get_object)

#     asyncio.run(main())
