import logging
from classes import S3Bucket
from quart import Blueprint, request, jsonify
from ai_workers import section_spec_detection, section_spec_requirements

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

section_specs_bp = Blueprint("section_specs", __name__)

@section_specs_bp.route("/section_spec_pages", methods=["POST"])
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

@section_specs_bp.route("/section_spec_requirements", methods=["POST"])
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
