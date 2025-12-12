from classes import S3Bucket
from ai_workers import division_breakdown
from quart import Blueprint, request, jsonify
from ai_workers import table_of_contents_detection

division_breakdown_bp = Blueprint("division_breakdown", __name__)

@division_breakdown_bp.route("/table_of_contents", methods=["POST"])
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

@division_breakdown_bp.route("/divisions_and_sections", methods=["POST"])
async def divisions_and_sections():
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
