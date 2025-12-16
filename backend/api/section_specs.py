import logging, datetime
from classes import S3Bucket
from quart import Blueprint, request, jsonify
from ai_workers import section_spec_detection, section_spec_requirements, primary_context_classification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

section_specs_bp = Blueprint("section_specs", __name__)

@section_specs_bp.route("/section_spec_pages", methods=["POST"])
async def section_spec_pages():
    data = await request.get_json()

    spec_id = data.get("spec_id")
    section_number = data.get("section_number")
    start_index = data.get("start_index", 0)
    end_index = data.get("end_index", None)

    start_time = datetime.datetime.now()

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

            section_spec_page_indices = await section_spec_detection(
                spec_id=spec_id,
                section_number=section_number,
                s3=s3,
                s3_client=s3_client,
                start_index=start_index,
                end_index=end_index
            )

            primary_and_context = await primary_context_classification(
                spec_id=spec_id,
                section_pages=section_spec_page_indices,
                s3=s3,
                s3_client=s3_client,
                section_number=section_number
            )

            return jsonify({
                **primary_and_context,
                "total_detected_pages": len(primary_and_context["primary"]) + len(primary_and_context["context"]),
                "run_time": f"{datetime.datetime.now() - start_time}"
            }), 200

    except Exception as e:
        logger.error(f"Error in section_spec_pages_detection: {e}")
        return jsonify({"error": str(e)}), 400

@section_specs_bp.route("/section_spec_requirements", methods=["POST"])
async def section_spec_reqs():
    data = await request.get_json()
    start_time = datetime.datetime.now()
    s3 = S3Bucket()

    spec_id = data.get("spec_id")
    primary_context = data.get("primary_context")
    primary_pages = primary_context["primary"]
    section_number = data.get("section_number")

    if spec_id is None:
        return jsonify({"error": "Spec ID is required"}), 400

    if primary_pages is None or len(primary_pages) == 0:
        return jsonify({"error": "Section pages are required"}), 400

    try:
        async with s3.s3_client() as s3_client:
            spec_check = await s3.get_original_pdf_with_client(spec_id=spec_id, s3_client=s3_client)
            if spec_check["status_code"] != 200:
                return jsonify({"error": "Spec ID is invalid"}), 400

            logger.info(f"Primary pages: {primary_pages}")
            # logger.info(f"Context pages: {context_pages}")

            section_spec_reqs = await section_spec_requirements(spec_id=spec_id, section_pages=primary_context, section_number=section_number, s3_client=s3_client)
    except Exception as e:
        logger.error(f"Error in section_spec_reqs: {e}")
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "section_spec_requirements": section_spec_reqs,
        "run_time": f"{datetime.datetime.now() - start_time}"
    }), 200
