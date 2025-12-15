import os, uuid, asyncio, logging
from classes import S3Bucket
from quart import Blueprint, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upload_routes_bp = Blueprint("upload_routes", __name__)

# Upload original PDF to S3 bucket
@upload_routes_bp.route("/upload_to_s3", methods=["POST"])
async def upload_to_s3():
    s3 = S3Bucket()
    files = await request.files
    pdf = files.getlist("pdf")

    if len(pdf) == 0 or pdf[0].content_type != "application/pdf" or not pdf[0].filename.endswith(".pdf"):
        return jsonify({"error": "No PDF file provided"}), 400

    spec_id = str(uuid.uuid4())

    async with s3.s3_client() as s3_client:
        original_pdf_upload_result = await s3.upload_original_pdf_with_client(files=pdf, spec_id=spec_id, s3=s3_client)

    return jsonify(original_pdf_upload_result), original_pdf_upload_result["status_code"]

# Upload and convert PDF to text or rasterize
@upload_routes_bp.route("/text_and_rasterize", methods=["POST"])
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
    if start_index < 0:
        return jsonify({"error": "Start index must be greater than or equal to 0"}), 400
    if end_index is not None and end_index < 0:
        return jsonify({"error": "End index must be greater than or equal to 0"}), 400
    if end_index is not None and end_index < start_index:
        return jsonify({"error": "End index must be greater than or equal to start index"}), 400

    s3 = S3Bucket()
    async with s3.s3_client() as s3_client:
        pdf_result = await s3.get_original_pdf_with_client(spec_id=spec_id, s3=s3_client)
        if pdf_result["status_code"] != 200:
            return jsonify({"error": pdf_result["data"]}), pdf_result["status_code"]

        pdf_bytes = pdf_result["data"]

        text_and_rasterize = await s3.bulk_upload_to_s3_with_client(
            pdf=pdf_bytes,
            spec_id=spec_id,
            s3=s3_client,
            dpi=dpi,
            grayscale=grayscale,
            rasterize_all=rasterize_all,
            start_index=start_index,
            end_index=end_index
        )

    return jsonify(text_and_rasterize), text_and_rasterize["status_code"]

# Upload original PDF to S3 bucket and convert PDF to text or rasterize
@upload_routes_bp.route("/upload_and_convert_pdf", methods=["POST"])
async def upload_and_convert_pdf():
    s3 = S3Bucket()

    # Consider switching to request.form instead of request.files
    files = await request.files
    pdf = files.getlist("pdf")

    if len(pdf) == 0:
        return jsonify({"error": "No PDF file provided"}), 400
    elif not pdf[0].content_type == "application/pdf" or not pdf[0].filename.endswith(".pdf"):
        return jsonify({"error": "Invalid PDF file"}), 400

    rasterize_all = files.get("rasterize_all", False)
    start_index = files.get("start_index", 0)
    end_index = files.get("end_index", None)
    dpi = files.get("dpi", 200)
    grayscale = files.get("grayscale", False)

    spec_id = str(uuid.uuid4())

    async with s3.s3_client() as s3_client:
        original_pdf_upload_result = await s3.upload_original_pdf_with_client(files=pdf, spec_id=spec_id, s3=s3_client)
        if original_pdf_upload_result["status_code"] != 200:
            return jsonify({"error": original_pdf_upload_result["data"]}), original_pdf_upload_result["status_code"]
        else:
            logger.info(f"Original PDF uploaded successfully to S3 bucket: {spec_id}")

        pdf_result = await s3.get_original_pdf_with_client(spec_id=spec_id, s3_client=s3_client)
        if pdf_result["status_code"] != 200:
            return jsonify({"error": pdf_result["data"]}), pdf_result["status_code"]

        pdf_bytes = pdf_result["data"]

        text_and_rasterize = await s3.bulk_upload_to_s3_with_client(
            pdf=pdf_bytes,
            spec_id=spec_id,
            s3_client=s3_client,
            dpi=dpi,
            grayscale=grayscale,
            rasterize_all=rasterize_all,
            start_index=start_index,
            end_index=end_index
        )

    return jsonify(text_and_rasterize), text_and_rasterize["status_code"]

@upload_routes_bp.route("/get_original_pdf/<spec_id>", methods=["GET"])
async def get_original_pdf(spec_id: str):
    s3 = S3Bucket()
    async with s3.s3_client() as s3_client:
        original_pdf = await s3.get_original_pdf_with_client(spec_id=spec_id, s3=s3_client)
        if original_pdf["status_code"] != 200:
            return jsonify({"error": original_pdf["data"]}), original_pdf["status_code"]

    return jsonify({"original_pdf": original_pdf["data"], "spec_id": spec_id}), original_pdf["status_code"]
