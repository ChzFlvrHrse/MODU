import logging
import json
import uuid
from classes import db, S3Bucket
from quart import Blueprint, jsonify, request
from classes import Anthropic, make_summary_schema
from csi_masterformat import divisions_and_sections

submittal_routes_bp = Blueprint("submittal_routes", __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

anthropic = Anthropic()


def required_fields(data: dict, fields: list) -> bool:
    missing_fields = []
    for field in fields:
        if field not in data:
            missing_fields.append(field)
    return len(missing_fields) == 0, missing_fields


@submittal_routes_bp.route("/create_submittal_package", methods=["POST"])
async def create_submittal_package():
    try:
        data = await request.json

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


@submittal_routes_bp.route("/upload_submittal", methods=["POST"])
async def upload_submittal():
    try:
        s3 = S3Bucket()

        form = await request.form
        files = await request.files

        pdf = files.get("pdf")
        spec_id = form.get("spec_id")
        package_id = form.get("package_id")
        submittal_title = form.get("submittal_title", pdf.filename)

        if not pdf:
            return jsonify({"error": "No file provided"}), 400
        if pdf.content_type != "application/pdf" or not pdf.filename.endswith(".pdf"):
            return jsonify({"error": "Invalid PDF file"}), 400

        is_valid, missing_fields = required_fields(form, ["spec_id", "package_id"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        file_uuid = str(uuid.uuid4())
        async with s3.s3_client() as s3_client:
            upload_result = await s3.upload_submittal_with_client(
                file=pdf,
                spec_id=spec_id,
                package_id=package_id,
                file_uuid=file_uuid,
                s3_client=s3_client
            )

        if upload_result.get("status_code") != 200:
            return jsonify({"error": upload_result.get("message")}), upload_result.get("status_code")

        logger.info(f"Submittal uploaded successfully to S3 bucket: {upload_result.get('s3_key')}")

        submittal_id = await db.create_submittal(
            package_id=package_id,
            submittal_title=submittal_title,
            s3_key=upload_result.get("s3_key"),
        )

        if not submittal_id:
            return jsonify({"error": "Failed to create submittal"}), 500

        return jsonify({"message": "Submittal created successfully", "submittal_id": submittal_id}), 200

    except Exception as e:
        logger.error(f"Error uploading submittal: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/upload_submittal_bulk", methods=["POST"])
async def upload_submittal_bulk():
    try:
        s3 = S3Bucket()

        form = await request.form
        files = await request.files

        if len(files) == 0:
            return jsonify({"error": "No files provided"}), 400
        if files[0].content_type != "application/pdf" or not files[0].filename.endswith(".pdf"):
            return jsonify({"error": "Invalid PDF file"}), 400

        spec_id = form.get("spec_id")
        if not spec_id:
            return jsonify({"error": "No spec_id provided"}), 400

    except Exception as e:
        logger.error(f"Error uploading submittal package: {e}")
        return jsonify({"error": str(e)}), 500
