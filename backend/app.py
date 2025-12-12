import logging
from quart_cors import cors
from quart import Quart
from api import (
    upload_routes_bp,
    division_breakdown_bp,
    section_specs_bp,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

quart_app = Quart(__name__)
quart_app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 100 # 100MB

quart_app = cors(
    quart_app,
    allow_origin="*",
    allow_headers="*",
    allow_methods=["GET", "POST", "DELETE", "UPDATE", "PUT", "PATCH"]
)

quart_app.register_blueprint(upload_routes_bp, url_prefix="/api/upload")
quart_app.register_blueprint(division_breakdown_bp, url_prefix="/api/division_breakdown")
quart_app.register_blueprint(section_specs_bp, url_prefix="/api/section_specs")

quart_app.run()
