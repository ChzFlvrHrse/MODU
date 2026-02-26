from quart import Blueprint
from .spec_routes import spec_routes_bp
from .summary_routes import summary_routes_bp

api_bp = Blueprint("api", __name__)

api_bp.register_blueprint(spec_routes_bp, url_prefix="/spec")
api_bp.register_blueprint(summary_routes_bp, url_prefix="/summary")
