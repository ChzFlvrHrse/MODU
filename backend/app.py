import logging
from api import api_bp
from quart import Quart
from quart_cors import cors
from classes import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 100 # 100MB

app = cors(
    app,
    allow_origin="*",
    allow_headers="*",
    allow_methods=["GET", "POST", "DELETE", "UPDATE", "PUT", "PATCH"]
)

app.register_blueprint(api_bp, url_prefix="/api")

@app.before_serving
async def init_db():
    await db.init_db()

app.run()
