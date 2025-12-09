from pathlib import Path
from quart_cors import cors
from classes.s3_buckets import S3Bucket
import os, logging, asyncio, sys, uuid
from quart import Quart, request, jsonify

# sys.path.insert(0, str(Path(__file__).parent.parent))
from classes.pdf_page_converter import PDFPageConverter

pdf_page_converter = PDFPageConverter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

quart_app = Quart(__name__)
quart_app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 100 # 100MB

quart_app = cors(
    quart_app,
    allow_origin="*",
    allow_headers="*",
    allow_methods=["GET", "POST", "DELETE", "UPDATE", "PUT", "PATCH"]
)

# Upload PDF directly to S3 bucket
@quart_app.route("/upload_to_s3", methods=["POST"])
async def upload_to_s3():
    s3 = S3Bucket()
    files = await request.files
    pdf = files.get("pdf")

    if pdf is None or pdf.filename == "":
        return jsonify({"error": "No PDF file provided"}), 400

    if not pdf.filename.endswith(".pdf"):
        return jsonify({"error": "Invalid file type. Please upload a PDF file."}), 400

    # spec_id = pdf.filename[:-4]
    spec_id = str(uuid.uuid4())

    loop = asyncio.get_running_loop()
    original_pdf_upload_result = await loop.run_in_executor(
        None,
        lambda: s3.upload_original_pdf_to_s3(
            file=pdf,
            file_name=pdf.filename,
            spec_id=spec_id,
        )
    )

    return jsonify(original_pdf_upload_result), original_pdf_upload_result["status_code"]

@quart_app.route("/original_pdf/<spec_id>", methods=["GET"])
async def get_original_pdf(spec_id: str):
    s3 = S3Bucket()
    original_pdf = s3.get_original_pdf(spec_id)
    return original_pdf

quart_app.run()
