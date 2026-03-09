import logging
import json
import uuid
from classes import db, S3Bucket, Anthropic
from quart import Blueprint, jsonify, request, Response
from quart.datastructures import FileStorage
from functions import stream_compliance_check
from typing import List, Optional

submittal_routes_bp = Blueprint("submittal_routes", __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = S3Bucket()
anthropic = Anthropic()


def required_fields(data: dict, fields: list) -> bool:
    missing_fields = []
    for field in fields:
        if field not in data:
            missing_fields.append(field)
    return len(missing_fields) == 0, missing_fields

# ---------------------------------------------------------------- Submittal Packages ----------------------------------------------------------------


@submittal_routes_bp.route("/create_submittal_package", methods=["POST"])
async def create_submittal_package():
    try:
        data: dict = await request.get_json()

        # required fields
        spec_id = data.get("spec_id")
        section_id = data.get("section_id")
        package_name = data.get("package_name")

        # optional fields
        company_name = data.get("company_name", None)
        submitted_by = data.get("submitted_by", None)
        submitted_date = data.get("submitted_date", None)
        compliance_score = data.get("compliance_score", None)
        status = data.get("status", "pending")

        is_valid, missing_fields = required_fields(
            data, ["spec_id", "section_id", "package_name"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        section = await db.get_packages_for_section(section_id)
        filter_packages_names = list(
            filter(lambda x: x.get("package_name") == package_name, section))

        if filter_packages_names:
            return jsonify({"error": f"Package name already exists: {filter_packages_names[0].get('package_name')}"}), 400

        # create submittal package
        submittal_package_id = await db.create_submittal_package(
            spec_id=spec_id,
            section_id=section_id,
            package_name=package_name,
            company_name=company_name,
            submitted_by=submitted_by,
            submitted_date=submitted_date,
            compliance_score=compliance_score,
            status=status
        )

        if not submittal_package_id:
            return jsonify({"error": "Failed to create submittal package"}), 500

        return jsonify({
            "message": "Submittal package created successfully",
            "package": {
                "submittal_package_id": submittal_package_id,
                **data,
                "status": status
            }
        }), 200

    except Exception as e:
        logger.error(f"Error creating submittal package: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/all_submittal_packages", methods=["GET"])
async def all_submittal_packages():
    try:
        data = request.args
        spec_id = data.get("spec_id")

        submittal_packages = await db.get_all_submittal_packages(spec_id)

        return jsonify({"submittal_packages": submittal_packages}), 200
    except Exception as e:
        logger.error(f"Error getting all submittal packages: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/sections_packages/<section_id>", methods=["GET"])
async def sections_packages(section_id: int):
    try:
        packages = await db.get_packages_for_section(section_id)
        if not packages:
            return jsonify({"error": "No packages found for section"}), 404

        return jsonify({"packages": packages}), 200
    except Exception as e:
        logger.error(f"Error getting packages for section: {section_id}: {e}")
        return jsonify({"error": f"Error getting packages for section: {section_id}: {str(e)}"}), 500


@submittal_routes_bp.route("/submittal_package", methods=["GET"])
async def submittal_package():
    try:
        data = request.args
        submittal_package_id = data.get("submittal_package_id")

        submittal_package = await db.get_submittal_package(submittal_package_id)

        return jsonify({"submittal_package": submittal_package}), 200
    except Exception as e:
        logger.error(f"Error getting submittal package: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------- Submittals ----------------------------------------------------------------


@submittal_routes_bp.route("/upload_submittal", methods=["POST"])
async def upload_submittal():
    try:
        s3 = S3Bucket()

        form: dict = await request.form
        files = await request.files

        spec_id = form.get("spec_id")
        package_id = form.get("package_id")

        is_valid, missing_fields = required_fields(
            form, ["spec_id", "package_id"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        pdfs = files.getlist("pdf")
        if not pdfs:
            return jsonify({"error": "No files provided"}), 400

        for pdf in pdfs:
            if pdf.content_type != "application/pdf" or not pdf.filename.endswith(".pdf"):
                return jsonify({"error": f"Invalid file: {pdf.filename}. PDFs only."}), 400

        VALID_SUBMITTAL_TYPE_IDS = {1042, 2187, 3561, 4823, 5394, 6718, 7265}
        results = []
        async with s3.s3_client() as s3_client:
            for i, pdf in enumerate(pdfs):
                submittal_type_id = int(form.get(f"submittal_type_id_{i}"))

                if submittal_type_id not in VALID_SUBMITTAL_TYPE_IDS:
                    return jsonify({"error": f"Invalid submittal type id: {submittal_type_id}"}), 400

                file_uuid = str(uuid.uuid4())
                upload_result = await s3.upload_submittal_with_client(
                    file=pdf,
                    spec_id=spec_id,
                    package_id=package_id,
                    file_uuid=file_uuid,
                    s3_client=s3_client,
                )

                if upload_result.get("status_code") != 200:
                    return jsonify({"error": upload_result.get("message")}), upload_result.get("status_code")

                submittal_title = form.get(
                    "submittal_title", pdf.filename.replace(".pdf", "").replace(".PDF", ""))
                submittal_id = await db.create_submittal(
                    package_id=package_id,
                    spec_id=spec_id,
                    submittal_title=submittal_title,
                    s3_key=upload_result.get("s3_key"),
                    submittal_type_id=submittal_type_id,
                )

                if not submittal_id:
                    return jsonify({"error": f"Failed to create DB record for {pdf.filename}"}), 500

                logger.info(
                    f"Submittal uploaded: {upload_result.get('s3_key')}")
                results.append({
                    "submittal_id": submittal_id,
                    "submittal_title": submittal_title,
                    "s3_key": upload_result.get("s3_key"),
                })

        return jsonify({
            "message": f"{len(results)} submittal(s) created successfully",
            "submittals": results,
        }), 200

    except Exception as e:
        logger.error(f"Error uploading submittal: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/compliance_check", methods=["POST"])
async def compliance_check_route():
    try:
        data: dict = await request.get_json()

        package_id = data.get("package_id")
        spec_id = data.get("spec_id")
        section_id = data.get("section_id")
        section_number = data.get("section_number")
        submittal_ids: Optional[List[int]] = data.get("submittal_ids", None)

        is_valid, missing_fields = required_fields(
            data, ["package_id", "spec_id", "section_number", "section_id"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        if submittal_ids:
            submittals = await db.get_submittals_by_ids(package_id, submittal_ids)
        else:
            submittals = await db.get_submittals_by_package(package_id)

        if not submittals:
            return jsonify({"status": "error", "error": "No submittals found"}), 404

        # Billing gate (testing)
        # prev_runs = await db.get_compliance_runs(package_id, submittal_id=submittal_ids[0] if submittal_ids else None)
        # if prev_runs:
        #     return jsonify({"error": "..."}), 400

        return Response(
            stream_compliance_check(
                package_id,
                spec_id,
                section_id,
                section_number,
                submittals,
                submittal_ids
            ),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        logger.error(f"Error in compliance_check_route: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/all_submittals", methods=["GET"])
async def all_submittals():
    try:
        data = request.args
        spec_id = data.get("spec_id")

        submittals = await db.get_all_submittals(spec_id)

        return jsonify({"submittals": submittals}), 200
    except Exception as e:
        logger.error(f"Error getting all submittals: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/get_submittal", methods=["GET"])
async def get_submittal():
    try:
        data = request.args
        submittal_id: int = data.get("submittal_id")

        submittal = await db.get_submittal(submittal_id)

        return jsonify({"submittal": submittal}), 200
    except Exception as e:
        logger.error(f"Error getting submittal: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/submittals_by_package", methods=["GET"])
async def submittals_by_package():
    try:
        data = request.args
        package_id = data.get("package_id")

        submittals = await db.get_all_submittals_by_package(package_id)

        return jsonify({"submittals": submittals}), 200
    except Exception as e:
        logger.error(f"Error getting submittals by package: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/submittals_by_ids", methods=["GET"])
async def submittals_by_ids():
    try:
        data = request.args
        submittal_ids: List[int] = data.get("submittal_ids")

        submittals = await db.get_submittals_by_ids(submittal_ids)

        return jsonify({"submittals": submittals}), 200
    except Exception as e:
        logger.error(f"Error getting submittals by ids: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/compliance_runs_for_package", methods=["GET"])
async def compliance_runs_for_package():
    try:
        data = request.args
        package_id: int = data.get("package_id")
        submittal_id: Optional[int] = data.get("submittal_id", None)

        is_valid, missing_fields = required_fields(
            data, ["package_id"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        compliance_runs = await db.get_compliance_runs(package_id, submittal_id=submittal_id)

        if not compliance_runs:
            return jsonify({"error": "No compliance runs found"}), 404

        return jsonify({"compliance_runs": compliance_runs}), 200
    except Exception as e:
        logger.error(f"Error getting compliance runs for package: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/get_compliance_run", methods=["GET"])
async def get_compliance_run():
    try:
        data = request.args
        compliance_run_id: int = data.get("compliance_run_id")

        compliance_run = await db.get_compliance_run(compliance_run_id)

        return jsonify(compliance_run), 200
    except Exception as e:
        logger.error(f"Error getting compliance run: {e}")
        return jsonify({"error": str(e)}), 500
