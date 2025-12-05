from pathlib import Path
from quart_cors import cors
import os, logging, asyncio, sys, uuid
from quart import Quart, request, jsonify

sys.path.insert(0, str(Path(__file__).parent.parent))
from helper_functions.rasterization import s3_bucket_uploader

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

# Upload PDF to S3 bucket
@quart_app.route("/upload_s3", methods=["POST"])
async def upload_pdf():
    files = await request.files
    pdf = files.get("pdf")

    if pdf is None or pdf.filename == "":
        return jsonify({"error": "No PDF file provided"}), 400

    if not pdf.filename.endswith(".pdf"):
        return jsonify({"error": "Invalid file type. Please upload a PDF file."}), 400

    spec_id = pdf.filename[:-4]

    loop = asyncio.get_event_loop()
    uploaded_result = loop.run_in_executor(
        None,
        lambda: s3_bucket_uploader(
            pdf_path=pdf.stream,
            spec_id=spec_id,
            grayscale=False,
        )
    )

    return jsonify({"uploaded_result": uploaded_result}), 200

quart_app.run()
