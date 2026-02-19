from quart import Blueprint
from .spec_routes import spec_routes_bp

api_bp = Blueprint("api", __name__)

api_bp.register_blueprint(spec_routes_bp, url_prefix="/spec")
