import logging, datetime
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
    start_index = data.get("start_index", 0)
    end_index = data.get("end_index", None)

    time_stamp = datetime.datetime.now().strftime("%H:%M:%S")

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

    try:
        async with s3.s3_client() as s3_client:
            # Validate spec_id exists (cheap-ish: list prefix)
            spec_check = await s3.check_pdf_exists_with_client(spec_id, s3_client)
            if not spec_check:
                return jsonify({"error": "PDF for spec ID does not exist"}), 400

            if end_index is None:
                end_index = await s3.get_original_page_count_with_client(spec_id, s3_client)

            section_spec_requirements = await section_spec_detection(
                spec_id=spec_id,
                section_number=section_number,
                s3=s3,
                s3_client=s3_client,
                start_index=start_index,
                end_index=end_index
            )

            return jsonify({
                "section_number": section_number,
                "section_spec_requirements": section_spec_requirements,
                "total_detected_pages": len(section_spec_requirements),
                "time_stamp": time_stamp
            }), 200

    except Exception as e:
        logger.error(f"Error in section_spec_pages_detection: {e}")
        return jsonify({"error": str(e)}), 400

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
