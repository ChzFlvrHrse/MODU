from quart import Blueprint
from .section_specs import section_specs_bp
from .upload_routes import upload_routes_bp
from .division_breakdown import division_breakdown_bp

api_bp = Blueprint("api", __name__)

api_bp.register_blueprint(upload_routes_bp, url_prefix="/upload")
api_bp.register_blueprint(division_breakdown_bp, url_prefix="/division_breakdown")
api_bp.register_blueprint(section_specs_bp, url_prefix="/section_specs")
