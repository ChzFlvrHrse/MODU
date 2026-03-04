from pydantic import BaseModel
from anthropic import AsyncAnthropic
import logging
import os
import asyncio
import aiohttp
import json
import base64
import fitz
import dotenv
from typing import Any, Dict, List, Sequence, Tuple, Optional, Type
from classes import S3Bucket

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PagePayload = Tuple[int, str, Optional[bytes], Optional[str]]

CONTEXT_WINDOW = 200000
CONTEXT_WINDOW_BUFFER = 0.9  # 90% of context window to be safe
MAX_SAFE_TOKENS = int(CONTEXT_WINDOW * CONTEXT_WINDOW_BUFFER)
ESTIMATED_TOKENS_PER_TEXT_PAGE = 1500
ESTIMATED_TOKENS_PER_IMAGE = 1000


class Anthropic:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def build_prompt(self, prompt: str, kwargs: dict) -> str:
        return prompt.format(**kwargs) if kwargs else prompt

    def page_blocks(self, page_index: int, text: str, image_bytes: Optional[bytes], media_type: Optional[str]) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = [
            {"type": "text", "text": f"===== PAGE {page_index} TEXT ====="},
            {"type": "text", "text": text or ""},
        ]

        if image_bytes:
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_bytes,
                },
            })
        return blocks

    def pdf_document_block(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(pdf_bytes).decode("utf-8"),
            }
        }

    def enforce_no_additional_properties(self, schema: Any) -> None:
        if not isinstance(schema, dict):
            return None

        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)

        # properties
        for v in schema.get("properties", {}).values():
            self.enforce_no_additional_properties(v)

        # arrays
        if isinstance(schema.get("items"), dict):
            self.enforce_no_additional_properties(schema["items"])

        # unions
        for key in ("anyOf", "oneOf", "allOf"):
            for sub in schema.get(key, []) or []:
                self.enforce_no_additional_properties(sub)

        # defs
        for sub in (schema.get("$defs") or {}).values():
            self.enforce_no_additional_properties(sub)

    async def claude(
        self,
        content_blocks: list[dict],
        system_prompt: str,
        schema: Type[BaseModel],
        max_tokens: int = 1024,
        model: str = "claude-sonnet-4-5-20250929"
    ) -> dict:
        try:
            response = await self.client.messages.parse(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                output_format=schema,
                messages=[
                    {
                        "role": "user",
                        "content": content_blocks,
                    }
                ]
            )
            return {
                "status": "success",
                "response": response.parsed_output.model_dump(),
            }
        except Exception as e:
            logger.error(f"Error calling Claude: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def split_batch(self, requests: Dict[str, Any]) -> Dict[str, Any]:
        batch_size = self.measure_batch_size(requests)

        if batch_size["status"] == "ok":
            return [requests]

        mid = len(requests) // 2
        if mid == 0:
            logger.error(
                "Cannot split further - single request exceeds limits")
            return [requests]

        left = self.split_batch(requests[:mid])
        right = self.split_batch(requests[mid:])
        return left + right

    async def count_tokens(
        self,
        content_blocks: list[tuple[str, bytes]],
        system_prompt: str,
        model: str = "claude-sonnet-4-5-20250929"
    ) -> int:
        try:
            content = []

            for text, img_bytes, media_type in content_blocks:
                if text:
                    content.append({
                        "type": "text",
                        "text": text
                    })

                if img_bytes:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_bytes,
                        }
                    })

            messages = [{
                "role": "user",
                "content": content
            }]

            res = await self.client.messages.count_tokens(
                model=model,
                system=system_prompt,
                messages=messages
            )

            return res.input_tokens
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return {
                "error": str(e),
                "status": "error",
            }

    def estimate_tokens(self, pages: Sequence[PagePayload]) -> int:
        total = 0
        for _, text, img_bytes, media_type in pages:
            if text:
                total += ESTIMATED_TOKENS_PER_TEXT_PAGE
            if img_bytes and media_type == "image/jpeg":
                total += ESTIMATED_TOKENS_PER_IMAGE
        return total

    async def check_tokens(
        self,
        pages: Sequence[PagePayload],
        system_prompt: str,
        model: str,
        custom_id: str
    ) -> bool:
        """Returns True if request is within context window, False otherwise."""
        estimate = self.estimate_tokens(pages)

        if estimate < MAX_SAFE_TOKENS * 0.5:
            logger.info(
                f"Request {custom_id} estimated at {estimate} tokens — skipping exact count")
            return True

        content_blocks = [(text, img, media_type)
                          for _, text, img, media_type in pages]
        exact_count = await self.count_tokens(content_blocks, system_prompt, model)

        if isinstance(exact_count, dict) and "error" in exact_count:
            logger.error(
                f"Token count failed for {custom_id}, skipping request")
            return False

        logger.info(f"Request {custom_id} exact token count: {exact_count}")

        if exact_count > MAX_SAFE_TOKENS:
            logger.warning(
                f"Request {custom_id} exceeds context window: {exact_count} / {self.MAX_SAFE_TOKENS} tokens")
            return False

        return True

    def measure_batch_size(self, requests: list[dict]) -> dict[str, Any]:
        MAX_REQUESTS = 10000
        SAFE_MB_LIMIT = 220
        HARD_MB_LIMIT = 256

        SAFE_LIMIT_BYTES = SAFE_MB_LIMIT * 1024 * 1024
        HARD_LIMIT_BYTES = HARD_MB_LIMIT * 1024 * 1024

        request_count = len(requests)
        if request_count > MAX_REQUESTS:
            return {
                "status": "error",
                "error_type": "request_count",
                "error": "Batch request count exceeds limit",
                "request_count": request_count,
                "max_requests": MAX_REQUESTS,
            }

        payload = {"requests": requests}

        # separators remove whitespace; ensure_ascii=False avoids \uXXXX expansion for unicode text
        raw = json.dumps(payload, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
        size_bytes = len(raw)
        size_mb = size_bytes / (1024 * 1024)

        metrics = {
            "request_count": request_count,
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 3),
            "safe_limit_mb": SAFE_MB_LIMIT,
            "hard_limit_mb": HARD_MB_LIMIT,
            "safe_limit_bytes": SAFE_LIMIT_BYTES,
            "hard_limit_bytes": HARD_LIMIT_BYTES,
            "headroom_bytes_to_hard_limit": max(0, HARD_LIMIT_BYTES - size_bytes),
            "headroom_mb_to_hard_limit": round(max(0.0, HARD_MB_LIMIT - size_mb), 3),
        }

        if size_bytes >= HARD_LIMIT_BYTES:
            logger.error(
                f"Batch exceeds hard limit: {metrics['size_mb']} MB / {HARD_MB_LIMIT} MB"
            )
            return {
                "status": "error",
                "error_type": "hard_memory_limit",
                "error": "Batch exceeds hard 256MB limit",
                **metrics,
            }

        if size_bytes >= SAFE_LIMIT_BYTES:
            logger.warning(
                f"Batch near limit — consider splitting: {metrics['size_mb']} MB / {SAFE_MB_LIMIT} MB"
            )
            return {
                "status": "warning",
                "warning_type": "near_memory_limit",
                "warning": "Batch near limit — consider splitting",
                **metrics,
            }

        logger.info(
            f"Batch size is within limits: {metrics['size_mb']} MB / {SAFE_MB_LIMIT} MB"
        )
        return {
            "status": "ok",
            **metrics,
        }

    async def build_claude_request(
        self,
        custom_id: str,
        # pages: Sequence[PagePayload],
        content_blocks: list[dict],
        system_prompt: str,
        schema: Type[BaseModel],
        max_tokens: int = 1024,
        model: str = "claude-sonnet-4-5-20250929"
    ) -> Dict[str, Any]:
        # Check token count before building request
        # NOTE: Develop a way to handle exceeding the context window by splitting the request into multiple requests
        # NOTE: Option 1: Split the request into multiple requests, custom_id will have -1, -2, -3, etc tacked on to the end, then re-run the results through claude to consolidate the results or just combine them manually
        # NOTE: Option 2: First attempt text + images, second attempt text only, then do option 1.
        # within_context = await self.check_tokens(pages, system_prompt, model, custom_id)
        # if not within_context:
        #     return None

        # for page_index, text, img, media_type in pages:
        #     content_blocks.extend(self.page_blocks(
        #         page_index, text, img, media_type))

        schema = schema.model_json_schema()
        if "type" not in schema:
            schema["type"] = "object"
        self.enforce_no_additional_properties(schema)

        return {
            "custom_id": str(custom_id),
            "params": {
                "model": model,
                "max_tokens": max_tokens,
                "system": [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [
                    {
                        "role": "user",
                        "content": content_blocks,
                    }
                ],
                "output_config": {
                    "format": {
                        "type": "json_schema",
                        "schema": schema,
                    }
                },
            },
        }

    async def create_batch(self, claude_requests: list[dict]) -> dict:
        try:
            batch = await self.client.messages.batches.create(requests=claude_requests)

            return {
                "batch_id": batch.id,
                "status": batch.processing_status,
                "request_counts": {
                    "processing": batch.request_counts.processing,
                    "succeeded": batch.request_counts.succeeded,
                    "errored": batch.request_counts.errored,
                    "canceled": batch.request_counts.canceled,
                    "expired": batch.request_counts.expired,
                },
            }

        except Exception as e:
            logger.error(f"Error creating batch: {e}")
            return {
                "error": str(e),
                "status": "error",
            }

    async def poll_and_fetch_batch_results(self, batch_id: str) -> list[dict]:
        while True:
            batch = await self.client.messages.batches.retrieve(batch_id)
            logger.info(
                f"Batch status: {batch.processing_status}, batch_id: {batch_id}")
            if batch.processing_status == "ended":
                break
            await asyncio.sleep(1)

        if not batch.results_url:
            return [{"error": "Batch ended but results_url is missing", "status": "error"}]

        headers = {
            "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(batch.results_url, headers=headers) as resp:
                    resp.raise_for_status()
                    text = await resp.text()

            parsed: list[dict] = []
            for line in text.splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)

                custom_id = row.get("custom_id")
                result = row.get("result", {})
                rtype = result.get("type")

                if rtype != "succeeded":
                    parsed.append({
                        "custom_id": custom_id,
                        "type": rtype,
                        "error": result.get("error")
                    })
                    continue

                msg = result.get("message", {})
                usage = msg.get("usage", {})
                blocks = msg.get("content", [])

                # find the first text block (structured output is usually here)
                text_block = next(
                    (b for b in blocks if b.get("type") == "text"), None)
                raw = (text_block or {}).get("text", "{}")

                try:
                    content = json.loads(raw)
                except Exception:
                    content = {"raw": raw}

                parsed.append({
                    "custom_id": custom_id,
                    "content": content,
                    "usage": usage,
                })

            return parsed

        except Exception as e:
            logger.error(f"Error fetching batch results: {e}")
            return [{"error": str(e), "status": "error"}]
