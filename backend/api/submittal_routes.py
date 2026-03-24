import logging
import json
import uuid
from classes import db, S3Bucket, Anthropic
from quart import Blueprint, jsonify, request
from functions import compliance_check, compare_compliance_runs
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
                "id": submittal_package_id,
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

        result = await compliance_check(
            package_id,
            spec_id,
            section_id,
            section_number,
            submittals,
            submittal_ids
        )

        if result.get("status") == "success":
            if submittal_ids:
                # Individual run — find by single submittal id
                prev_runs = await db.get_compliance_runs(package_id, submittal_id=submittal_ids[0])
                if prev_runs:
                    await db.update_compliance_run(
                        compliance_run_id=prev_runs[0].get("id"),
                        submittal_ids=result.get("submittal_ids"),
                        compliance_result=result.get("result"),
                        compliance_score=result.get(
                            "result").get("compliance_score"),
                        is_compliant=result.get("result").get("is_compliant"),
                        pipeline=result.get("pipeline"),
                        run_type="individual",
                        prompt_version=int(
                            prev_runs[0].get("prompt_version")) + 1,
                        token_count=result.get("total_tokens"),
                    )
                else:
                    await db.create_compliance_run(
                        package_id=package_id,
                        spec_id=spec_id,
                        section_id=section_id,
                        submittal_ids=result.get("submittal_ids"),
                        compliance_result=result.get("result"),
                        compliance_score=result.get(
                            "result").get("compliance_score"),
                        is_compliant=result.get("result").get("is_compliant"),
                        pipeline=result.get("pipeline"),
                        run_type="individual",
                        model="claude-sonnet-4-6",
                        token_count=result.get("total_tokens"),
                    )
            else:
                # Package/cumulative run — find by run_type
                prev_run = await db.get_compliance_runs(package_id, run_type="package")
                prev_run = prev_run[0] if prev_run else None
                if prev_run:
                    await db.update_compliance_run(
                        compliance_run_id=prev_run.get("id"),
                        submittal_ids=result.get("submittal_ids"),
                        compliance_result=result.get("result"),
                        compliance_score=result.get(
                            "result").get("compliance_score"),
                        is_compliant=result.get("result").get("is_compliant"),
                        pipeline=result.get("pipeline"),
                        run_type="package",
                        prompt_version=int(prev_run.get("prompt_version")) + 1,
                        token_count=result.get("total_tokens"),
                    )
                else:
                    await db.create_compliance_run(
                        package_id=package_id,
                        spec_id=spec_id,
                        section_id=section_id,
                        submittal_ids=result.get("submittal_ids"),
                        compliance_result=result.get("result"),
                        compliance_score=result.get(
                            "result").get("compliance_score"),
                        is_compliant=result.get("result").get("is_compliant"),
                        pipeline=result.get("pipeline"),
                        run_type="package",
                        model="claude-sonnet-4-6",
                        token_count=result.get("total_tokens"),
                    )

                updated_package = await db.update_package_after_run(
                    package_id=package_id,
                    compliance_result=result.get("result"),
                    compliance_score=result.get("result").get("compliance_score"),
                    checked_submittal_ids=result.get("submittal_ids"),
                )

                if not updated_package:
                    return jsonify({"error": "Failed to update package after run"}), 500

            return jsonify({
                "message": "Compliance check completed successfully",
                "compliance_check": result,
                "success": True,
            }), 200

        return jsonify({"error": result.get("error"), "success": False}), 500

    except Exception as e:
        logger.error(f"Error in compliance_check_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500


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

        submittals = await db.get_submittals_by_package(package_id)

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
        run_type: Optional[str] = data.get("run_type", None)

        is_valid, missing_fields = required_fields(
            data, ["package_id"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        compliance_runs = await db.get_compliance_runs(package_id, submittal_id=submittal_id, run_type=run_type)

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


@submittal_routes_bp.route("/package_result/<int:package_id>", methods=["GET"])
async def package_result(package_id: int):
    try:
        result = await db.get_package_result(package_id)
        if not result or not result.get("compliance_result"):
            return jsonify({"error": "No compliance result found"}), 404
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"Error getting package result: {e}")
        return jsonify({"error": str(e)}), 500


@submittal_routes_bp.route("/compare_compliance", methods=["POST"])
async def compare_compliance():
    try:
        data: dict = await request.get_json()

        package_id_1: int = data.get("package_id_1")
        package_id_2: int = data.get("package_id_2")
        section_id: int = data.get("section_id")
        section_number: str = data.get("section_number")

        is_valid, missing_fields = required_fields(
            data, ["package_id_1", "package_id_2", "section_number", "section_id"])
        if not is_valid:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        result = await compare_compliance_runs(
            package_id_1,
            package_id_2,
            section_number
        )

        if result.get("status") == "success":
            await db.create_compliance_comparison(
                package_id_a=package_id_1,
                package_id_b=package_id_2,
                section_id=section_id,
                section_number=section_number,
                overall_winner=result.get("result").get("overall_winner"),
                package_name_a=result.get("package_a_name"),
                package_name_b=result.get("package_b_name"),
                score_a=result.get("result").get("score_a"),
                score_b=result.get("result").get("score_b"),
                score_delta=result.get("result").get("score_delta"),
                executive_summary=result.get("result").get("executive_summary"),
                recommendation=result.get("result").get("recommendation"),
                comparison_result=json.dumps(result.get("result")),
                model_version="claude-sonnet-4-6",
            )

            return jsonify({
                **result,
                "success": True,
            }), 200
        else:
            return jsonify({"error": result.get("error"), "success": False}), 500

    except Exception as e:
        logger.error(f"Error comparing compliance results: {e}")
        return jsonify({"error": str(e)}), 500

@submittal_routes_bp.route("/compliance_comparisons", methods=["GET"])
async def compliance_comparisons():
    try:
        data = request.args
        id: Optional[int] = data.get("id", None)
        section_id: Optional[int] = data.get("section_id", None)

        compliance_comparisons = await db.get_compliance_comparisons(id=id, section_id=section_id)
        if not compliance_comparisons:
            return jsonify({"error": "No compliance comparisons found"}), 404

        return jsonify(compliance_comparisons), 200
    except Exception as e:
        logger.error(f"Error getting compliance comparisons: {e}")
        return jsonify({"error": str(e)}), 500

@submittal_routes_bp.route("/get_compliance_comparisons_list", methods=["GET"])
async def get_compliance_comparisons_list ():
    try:
        section_id = request.args.get("section_id", None)
        if not section_id:
            return jsonify({"error": "section_id is required"}), 400

        comparison_ids = await db.get_compliance_comparisons_list(section_id=int(section_id))
        return jsonify({"comparisons": comparison_ids}), 200
    except Exception as e:
        logger.error(f"Error getting compliance comparison ids: {e}")
        return jsonify({"error": str(e)}), 500

@submittal_routes_bp.route("/package/<int:package_id>/chosen", methods=["PATCH"])
async def update_package_chosen_route(package_id: int):
    try:
        data: dict = await request.get_json()

        is_chosen = data.get("is_chosen")
        if is_chosen is None:
            return jsonify({"error": "is_chosen is required"}), 400

        if not isinstance(is_chosen, bool):
            return jsonify({"error": "is_chosen must be a boolean"}), 400

        package = await db.get_submittal_package(package_id)
        if not package:
            return jsonify({"error": "Package not found"}), 404

        result = await db.update_package_chosen(
            package_id=package_id,
            is_chosen=is_chosen,
        )

        if result.get("error"):
            return jsonify(result), 500

        return jsonify({
            "success": True,
            "package_id": package_id,
            "is_chosen": is_chosen,
        }), 200

    except Exception as e:
        logger.error(f"Error in update_package_chosen_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@submittal_routes_bp.route("/commit_section_packages", methods=["POST"])
async def commit_section_packages_route():
    try:
        data: dict = await request.get_json()

        section_id = data.get("section_id")
        chosen_package_ids = data.get("chosen_package_ids")

        if not section_id:
            return jsonify({"error": "section_id is required"}), 400
        if chosen_package_ids is None or not isinstance(chosen_package_ids, list):
            return jsonify({"error": "chosen_package_ids must be a list"}), 400

        result = await db.commit_section_packages(
            section_id=int(section_id),
            chosen_package_ids=chosen_package_ids,
        )

        if result.get("error"):
            return jsonify(result), 500

        return jsonify({
            "success": True,
            **result,
        }), 200

    except Exception as e:
        logger.error(f"Error in commit_section_packages_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500

@submittal_routes_bp.route("/delete_submittal_package", methods=["DELETE"])
async def delete_submittal_package_route():
    try:
        data = request.args
        package_id: int = data.get("package_id")

        if not package_id:
            return jsonify({"error": "package_id is required"}), 400

        result = await db.delete_submittal_package(package_id)
        if result.get("error"):
            return jsonify({"error": result.get("error"), "success": False}), 500

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Error in delete_submittal_package_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500
