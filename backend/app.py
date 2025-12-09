from pathlib import Path
from quart_cors import cors
import os, logging, asyncio, sys, uuid, fitz
from quart import Quart, request, jsonify

# sys.path.insert(0, str(Path(__file__).parent.parent))
# from classes.s3_buckets import S3Bucket
# from classes.pdf_page_converter import PDFPageConverter
from classes import PDFPageConverter, S3Bucket, Tesseract
from ai_workers import division_breakdown

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
        lambda: s3.upload_original_pdf(
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

@quart_app.route("/text_and_rasterize", methods=["POST"])
async def text_and_rasterize():
    data = await request.json

    spec_id = data.get("spec_id")
    start_index = data.get("start_index", 0)
    end_index = data.get("end_index", None)
    rasterize_all = data.get("rasterize_all", False)
    dpi = data.get("dpi", 200)
    grayscale = data.get("grayscale", False)

    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400

    s3 = S3Bucket()
    pdf_bytes = s3.get_original_pdf(spec_id)["data"]

    text_and_rasterize = s3.bulk_upload_to_s3(pdf=pdf_bytes, spec_id=spec_id, rasterize_all=rasterize_all, start_index=start_index, end_index=end_index, dpi=dpi, grayscale=grayscale)
    return jsonify(text_and_rasterize), 200

@quart_app.route("/divisions_and_sections", methods=["POST"])
async def divisons_and_sections():
    data = await request.json

    spec_id = data.get("spec_id")
    batch_size = data.get("batch_size", 10)
    start_index = data.get("start_index", 0)
    end_index = data.get("end_index", None)

    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400

    divisions_and_sections = await division_breakdown(spec_id=spec_id, batch_size=batch_size, start_index=start_index, end_index=end_index)
    return jsonify(divisions_and_sections), 200

quart_app.run()
