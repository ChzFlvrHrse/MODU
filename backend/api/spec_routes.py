import logging
import datetime
import uuid
import base64
from functions import page_classification
from quart import Blueprint, request, jsonify, current_app
from classes import S3Bucket, db, Anthropic, PDFPageConverter
from functions import section_pages_detection as detect_section_pages
from csi_masterformat import divisions_and_sections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

spec_routes_bp = Blueprint("spec_routes", __name__)

anthropic = Anthropic()


# Upload original PDF to S3 bucket and convert PDF to text or rasterize
@spec_routes_bp.route("/upload", methods=["POST"])
async def upload():
    s3 = S3Bucket()
    start_time = datetime.datetime.now()

    form = await request.form
    files = await request.files
    pdf = files.getlist("pdf")

    if len(pdf) == 0:
        return jsonify({"error": "No PDF file provided"}), 400
    if pdf[0].content_type != "application/pdf" or not pdf[0].filename.endswith(".pdf"):
        return jsonify({"error": "Invalid PDF file"}), 400

    # User can provide a project name or it will default to the pdf filename
    project_name = form.get("project_name", pdf[0].filename)

    spec_id = str(uuid.uuid4())

    async with s3.s3_client() as s3_client:
        original_pdf_upload_result = await s3.upload_original_pdf_with_client(files=pdf, spec_id=spec_id, s3=s3_client)
        if original_pdf_upload_result["status_code"] != 200:
            return jsonify({"error": original_pdf_upload_result["data"]}), original_pdf_upload_result["status_code"]

        logger.info(
            f"Original PDF uploaded successfully to S3 bucket: {spec_id}")

        pdf_result = await s3.get_original_pdf_with_client(spec_id=spec_id, s3_client=s3_client)
        if pdf_result["status_code"] != 200:
            return jsonify({"error": pdf_result["data"]}), pdf_result["status_code"]

        await s3.upload_original_pdf_pages(pdf=pdf_result["data"], spec_id=spec_id, s3_client=s3_client)

        section_page_dict = await detect_section_pages(spec_id, s3, s3_client)

        await db.create_project(spec_id, project_name)

        total_divisions = 0
        total_sections = 0
        for division, sections in section_page_dict["divisions_and_sections"].items():
            total_divisions += 1
            division_title = divisions_and_sections[division][f"{division}0000"]
            division_id = await db.create_division(spec_id, division, division_title)
            for section_number, pages in sections.items():
                total_sections += 1
                section_title = pages.get(
                    "title", "Undocumented Section Number (MSF2020)")

                total_pages = sum(len(page) for page in pages.get("multi", []))
                total_pages += len(pages.get("single", []))
                pages["total_pages"] = total_pages

                await db.create_section(spec_id, division, division_id, section_number, section_title, total_pages)

        await db.update_project(
            spec_id,
            total_divisions=total_divisions,
            total_sections=total_sections,
        )

    current_app.add_background_task(
        page_classification,
        spec_id,
        section_page_dict["divisions_and_sections"]
    )

    return jsonify({
        "run_time": f"{datetime.datetime.now() - start_time}",
        # "text_and_rasterize": text_and_rasterize,
        "section_page_index": section_page_dict
    }), 200


@spec_routes_bp.route("/projects", methods=["GET"])
async def get_projects():
    try:
        projects = await db.get_projects()
        logger.info(f"Projects: {len(projects)} projects")
        return jsonify({"projects": projects}), 200
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return jsonify({"error": str(e)}), 500


@spec_routes_bp.route("/spec_sections/<spec_id>", methods=["GET"])
async def get_spec_sections(spec_id: str):
    try:
        spec_sections = await db.get_all_sections(spec_id)
        logger.info(f"Spec sections: {len(spec_sections)} sections")
        return jsonify({"spec_sections": spec_sections}), 200
    except Exception as e:
        logger.error(f"Error getting spec requirements: {e}")
        return jsonify({"error": str(e)}), 500


@spec_routes_bp.route("/sections_with_primary_pages/<spec_id>", methods=["GET"])
async def sections_with_primary_pages(spec_id: str):
    try:
        sections_with_primary_pages = await db.get_sections_with_primary_pages(spec_id)
        logger.info(
            f"Sections with primary pages: {sections_with_primary_pages}")
        return jsonify({"sections_primary_pages": sections_with_primary_pages}), 200
    except Exception as e:
        logger.error(f"Error getting sections with primary pages: {e}")
        return jsonify({"error": str(e)}), 500


@spec_routes_bp.route("/delete/project/<spec_id>", methods=["DELETE"])
async def delete_project(spec_id: str):
    try:
        await db.delete_project(spec_id)
        logger.info(f"Project deleted successfully: {spec_id}")
        return jsonify({"success": True, "spec_id": spec_id}), 200
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({"error": str(e)}), 500


@spec_routes_bp.route("/lifecycle/<int:section_id>", methods=["PATCH"])
async def update_section_lifecycle_route(section_id: int):
    try:
        data: dict = await request.get_json()

        lifecycle_status = data.get("lifecycle_status")
        chosen_packages = data.get("chosen_packages")
        override = data.get("override")

        # Validate lifecycle_status if provided
        valid_statuses = {"pending", "in_progress", "complete", "excluded"}
        if lifecycle_status and lifecycle_status not in valid_statuses:
            return jsonify({"error": f"Invalid lifecycle_status. Must be one of: {', '.join(valid_statuses)}"}), 400

        # Need spec_id and division to trigger rollup — fetch from section
        section = await db.get_section_by_id(section_id)
        if not section:
            return jsonify({"error": "Section not found"}), 404

        result = await db.update_section_lifecycle(
            section_id=section_id,
            lifecycle_status=lifecycle_status,
            chosen_packages=chosen_packages,
            override=override,
        )

        if result.get("error"):
            return jsonify(result), 500

        # Trigger rollup
        division_score = await db.compute_division_completion(
            spec_id=section["spec_id"],
            division=section["division"],
        )
        project_score = await db.compute_project_completion(
            spec_id=section["spec_id"],
        )

        return jsonify({
            "success": True,
            "section_id": section_id,
            "lifecycle_status": result.get("lifecycle_status"),
            "chosen_packages": result.get("chosen_packages"),
            "division_score": division_score,
            "project_score": project_score,
        }), 200

    except Exception as e:
        logger.error(f"Error in update_section_lifecycle_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@spec_routes_bp.route("/lifecycle/summary/<string:spec_id>", methods=["GET"])
async def get_lifecycle_summary_route(spec_id: str):
    try:
        summary = await db.get_lifecycle_summary(spec_id)
        return jsonify({"success": True, "summary": summary}), 200

    except Exception as e:
        logger.error(f"Error in get_lifecycle_summary_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@spec_routes_bp.route("/lifecycle/division/<string:spec_id>/<string:division>", methods=["GET"])
async def get_division_completion_route(spec_id: str, division: str):
    try:
        score = await db.compute_division_completion(spec_id=spec_id, division=division)
        return jsonify({"success": True, "spec_id": spec_id, "division": division, "score": score}), 200

    except Exception as e:
        logger.error(f"Error in get_division_completion_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@spec_routes_bp.route("/lifecycle/project/<string:spec_id>", methods=["GET"])
async def get_project_completion_route(spec_id: str):
    try:
        score = await db.compute_project_completion(spec_id=spec_id)
        return jsonify({"success": True, "spec_id": spec_id, "score": score}), 200

    except Exception as e:
        logger.error(f"Error in get_project_completion_route: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@spec_routes_bp.route("/section_pdf_pages", methods=["GET"])
async def get_section_pdf_pages_route():
    try:
        spec_id = request.args.get("spec_id")
        section_number = request.args.get("section_number")

        s3 = S3Bucket()
        if not spec_id or not section_number:
            return jsonify({"error": "spec_id and section_number are required"}), 400

        pages = await db.get_section_pdf_pages(spec_id, section_number)
        if not pages.get("success"):
            return jsonify({"error": pages.get("error"), "success": False}), 500

        primary_pages = pages.get("primary_pages")
        reference_pages = pages.get("reference_pages")

        primary_pdf_pages = []
        reference_pdf_pages = []
        async with s3.s3_client() as s3_client:
            for page in primary_pages:
                key = f"{spec_id}/original_pages/page_{page:04d}.pdf"
                result = await s3.pdf_page_to_png(key, s3_client)
                if result.get("success"):
                    primary_pdf_pages.append({
                        "bytes": result.get("bytes"),
                        "media_type": result.get("media_type")
                    })
            for page in reference_pages:
                key = f"{spec_id}/original_pages/page_{page:04d}.pdf"
                result = await s3.pdf_page_to_png(key, s3_client)
                if result.get("success"):
                    reference_pdf_pages.append({
                        "bytes": result.get("bytes"),
                        "media_type": result.get("media_type")
                    })

        return jsonify({
            "success": True,
            "spec_id": spec_id,
            "section_number": section_number,
            "primary_pdf_pages": primary_pdf_pages,
            "reference_pdf_pages": reference_pdf_pages
        }), 200

    except Exception as e:
        logger.error(f"Error in get_section_pages: {e}")
        return jsonify({"error": str(e), "success": False}), 500
