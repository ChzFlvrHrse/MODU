import logging, datetime, uuid
from functions import page_classification
from quart import Blueprint, request, jsonify, current_app
from classes import S3Bucket, db, Anthropic
from functions import section_pages_detection as detect_section_pages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

spec_routes_bp = Blueprint("spec_routes", __name__)

anthropic = Anthropic()


# Upload original PDF to S3 bucket and convert PDF to text or rasterize
@spec_routes_bp.route("/upload", methods=["POST"])
async def upload():
    s3 = S3Bucket()
    start_time = datetime.datetime.now()

    # Consider switching to request.form instead of request.files
    files = await request.files
    pdf = files.getlist("pdf")
    # User can provide a project name or it will default to the pdf filename
    project_name = files.get("project_name", pdf[0].filename)

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
            logger.info(
                f"Original PDF uploaded successfully to S3 bucket: {spec_id}")

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

        section_page_dict = await detect_section_pages(spec_id, s3, s3_client)

        await db.save_project(spec_id, project_name)

        total_divisions = 0
        total_sections = 0
        for division, sections in section_page_dict["divisions_and_sections"].items():
            total_divisions += 1
            for section_number, pages in sections.items():
                total_sections += 1
                section_title = pages.get(
                    "title", "Undocumented Section Number (MSF2020)")

                total_pages = 0
                for page in pages.get("multi", []):
                    total_pages += len(page)
                total_pages += len(pages.get("single", []))
                pages["total_pages"] = total_pages
                await db.save_section(spec_id, division, section_number, section_title, total_pages)

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
        "text_and_rasterize": text_and_rasterize,
        "section_page_index": section_page_dict
    }), text_and_rasterize["status_code"]


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
        return jsonify({"message": "Project deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({"error": str(e)}), 500
