from quart import Blueprint
from .upload_routes import upload_routes_bp
from .spec_routes import spec_routes_bp

api_bp = Blueprint("api", __name__)

api_bp.register_blueprint(upload_routes_bp, url_prefix="/upload")
api_bp.register_blueprint(spec_routes_bp, url_prefix="/spec")
