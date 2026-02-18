import logging
from quart import Blueprint, jsonify
from classes import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

spec_routes_bp = Blueprint("spec_routes", __name__)

@spec_routes_bp.route("/projects", methods=["GET"])
async def get_projects():
    try:
        projects = await db.get_projects()
        logger.info(f"Projects: {projects}")
        return jsonify({"projects": projects}), 200
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return jsonify({"error": str(e)}), 500

@spec_routes_bp.route("/all_spec_sections/<spec_id>", methods=["GET"])
async def all_spec_sections(spec_id: str):
    try:
        spec_sections = await db.get_all_spec_sections(spec_id)
        logger.info(f"Spec sections: {spec_sections}")
        return jsonify({"spec_sections": spec_sections}), 200
    except Exception as e:
        logger.error(f"Error getting spec requirements: {e}")
        return jsonify({"error": str(e)}), 500

@spec_routes_bp.route("/all_specs_with_primary_pages/<spec_id>", methods=["GET"])
async def all_specs_with_primary_pages(spec_id: str):
    try:
        specs_with_primary_pages = await db.get_all_specs_with_primary_pages(spec_id)
        logger.info(f"Specs with primary pages: {specs_with_primary_pages}")
        return jsonify({"specs_with_primary_pages": specs_with_primary_pages}), 200
    except Exception as e:
        logger.error(f"Error getting specs with primary pages: {e}")
        return jsonify({"error": str(e)}), 500
