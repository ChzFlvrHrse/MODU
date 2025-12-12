from quart_cors import cors
import os, logging, asyncio, uuid, fitz
from quart import Quart, request, jsonify
from classes import PDFPageConverter, S3Bucket, Tesseract
from ai_workers import (
    division_breakdown,
    section_spec_detection,
    section_spec_requirements,
    table_of_contents_detection
)

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
    pdf = files.getlist("pdf")

    if len(pdf) == 0 or pdf[0].content_type != "application/pdf" or not pdf[0].filename.endswith(".pdf"):
        return jsonify({"error": "No PDF file provided"}), 400

    spec_id = str(uuid.uuid4())

    loop = asyncio.get_running_loop()
    original_pdf_upload_result = await loop.run_in_executor(
        None,
        lambda: s3.upload_original_pdf(
            files=pdf,
            spec_id=spec_id,
        )
    )

    return jsonify(original_pdf_upload_result), original_pdf_upload_result["status_code"]

@quart_app.route("/original_pdf/<spec_id>", methods=["GET"])
async def get_original_pdf(spec_id: str):
    s3 = S3Bucket()
    original_pdf = s3.get_original_pdf(spec_id)

    if original_pdf["status_code"] != 200:
        return jsonify({"error": original_pdf["data"]}), original_pdf["status_code"]

    return jsonify({"original_pdf": original_pdf["data"], "spec_id": spec_id}), original_pdf["status_code"]

# Upload and convert PDF to text or rasterize
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
    if start_index < 0:
        return jsonify({"error": "Start index must be greater than or equal to 0"}), 400
    if end_index is not None and end_index < 0:
        return jsonify({"error": "End index must be greater than or equal to 0"}), 400
    if end_index is not None and end_index < start_index:
        return jsonify({"error": "End index must be greater than or equal to start index"}), 400

    s3 = S3Bucket()
    loop = asyncio.get_running_loop()
    pdf_result = await loop.run_in_executor(
        None,
        lambda: s3.get_original_pdf(spec_id)
    )
    if pdf_result["status_code"] != 200:
        return jsonify({"error": pdf_result["data"]}), pdf_result["status_code"]

    pdf_bytes = pdf_result["data"]

    loop = asyncio.get_running_loop()
    text_and_rasterize = await loop.run_in_executor(
        None,
        lambda: s3.bulk_upload_to_s3(pdf=pdf_bytes, spec_id=spec_id, rasterize_all=rasterize_all, start_index=start_index, end_index=end_index, dpi=dpi, grayscale=grayscale)
    )

    # if text_and_rasterize["status_code"] != 200:
    #     return jsonify({"error": text_and_rasterize["data"]}), text_and_rasterize["status_code"]

    return jsonify({"upload_data": text_and_rasterize}), 200

@quart_app.route("/upload_and_convert_pdf", methods=["POST"])
async def upload_and_convert_pdf():
    s3 = S3Bucket()
    files = await request.files

    pdf = files.getlist("pdf")
    if not pdf[0].content_type == "application/pdf" or not pdf[0].filename.endswith(".pdf"):
        return jsonify({"error": "No PDF file provided"}), 400

    rasterize_all = files.get("rasterize_all", False)
    start_index = files.get("start_index", 0)
    end_index = files.get("end_index", None)
    dpi = files.get("dpi", 200)
    grayscale = files.get("grayscale", False)

    spec_id = str(uuid.uuid4())

    loop = asyncio.get_running_loop()
    original_pdf_upload_result = await loop.run_in_executor(
        None,
        lambda: s3.upload_original_pdf(
            files=pdf,
            spec_id=spec_id
        )
    )
    if original_pdf_upload_result["status_code"] != 200:
        return jsonify({"error": original_pdf_upload_result["data"]}), original_pdf_upload_result["status_code"]
    else:
        logger.info(f"Original PDF uploaded successfully to S3 bucket: {spec_id}")

    pdf_result = await loop.run_in_executor(
        None,
        lambda: s3.get_original_pdf(spec_id)
    )
    if pdf_result["status_code"] != 200:
        return jsonify({"error": pdf_result["data"]}), pdf_result["status_code"]

    pdf_bytes = pdf_result["data"]

    text_and_rasterize = await loop.run_in_executor(
        None,
        lambda: s3.bulk_upload_to_s3(pdf=pdf_bytes, spec_id=spec_id, rasterize_all=rasterize_all, start_index=start_index, end_index=end_index, dpi=dpi, grayscale=grayscale)
    )

    return jsonify({"upload_data": text_and_rasterize}), 200

@quart_app.route("/table_of_contents", methods=["POST"])
async def table_of_contents():
    data = await request.json

    spec_id = data.get("spec_id")
    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400

    table_of_contents = await table_of_contents_detection(spec_id)

    if table_of_contents["status_code"] != 200:
        return jsonify({"error": table_of_contents["error"]}), table_of_contents["status_code"]
    else:
        return jsonify({"toc_indices": table_of_contents["toc_indices"]}), table_of_contents["status_code"]

@quart_app.route("/divisions_and_sections", methods=["POST"])
async def divisons_and_sections():
    data = await request.json

    spec_id = data.get("spec_id")
    toc_indices = data.get("toc_indices", [])
    batch_size = data.get("batch_size", 10)
    start_index = data.get("start_index", 0)
    end_index = data.get("end_index", None)

    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400

    if toc_indices is None or len(toc_indices) == 0:
        return jsonify({"error": "TOC indices are required"}), 400

    if start_index < 0:
        return jsonify({"error": "Start index must be greater than or equal to 0"}), 400
    # if end_index < 0:
    #     return jsonify({"error": "End index must be greater than or equal to 0"}), 400
    # if end_index < start_index:
    #     return jsonify({"error": "End index must be greater than or equal to start index"}), 400

    s3 = S3Bucket()

    spec_check = s3.get_original_pdf(spec_id)
    if spec_check["status_code"] != 200:
        return jsonify({"error": "Spec ID is invalid"}), 400

    divisions_and_sections = await division_breakdown(spec_id=spec_id, toc_indices=toc_indices, batch_size=batch_size, start_index=start_index, end_index=end_index)
    return jsonify(divisions_and_sections), 200

@quart_app.route("/section_spec_pages", methods=["POST"])
async def section_spec_pages():
    data = await request.json

    spec_id = data.get("spec_id")
    section_number = data.get("section_number")
    batch_size = data.get("batch_size", 10)
    start_index = data.get("start_index", 0)
    end_index = data.get("end_index", None)

    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400
    if section_number is None:
        return jsonify({"error": "Section number is required"}), 400

    if start_index < 0:
        return jsonify({"error": "Start index must be greater than or equal to 0"}), 400
    if end_index is not None and end_index < 0:
        return jsonify({"error": "End index must be greater than or equal to 0"}), 400
    if end_index is not None and end_index < start_index:
        return jsonify({"error": "End index must be greater than or equal to start index"}), 400

    s3 = S3Bucket()
    if end_index is None:
        end_index = s3.get_original_page_count(spec_id)

    spec_check = s3.get_original_pdf(spec_id)
    if spec_check["status_code"] != 200:
        return jsonify({"error": "Spec ID is invalid"}), 400

    section_spec_requirements = await section_spec_detection(spec_id=spec_id, section_number=section_number, batch_size=batch_size, start_index=start_index, end_index=end_index)

    return jsonify({"section_number": section_number, "section_spec_requirements": section_spec_requirements}), 200

@quart_app.route("/section_spec_requirements", methods=["POST"])
async def section_spec_reqs():
    data = await request.json

    spec_id = data.get("spec_id")
    section_pages = data.get("section_pages")

    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400

    if section_pages is None or len(section_pages) == 0:
        return jsonify({"error": "Section pages are required"}), 400

    s3 = S3Bucket()
    spec_check = s3.get_original_pdf(spec_id)
    if spec_check["status_code"] != 200:
        return jsonify({"error": "Spec ID is invalid"}), 400

    logger.info(f"Section pages: {section_pages}")

    section_spec_reqs = await section_spec_requirements(spec_id=spec_id, section_pages=section_pages)

    return jsonify({"section_spec_requirements": section_spec_reqs}), 200

quart_app.run()
