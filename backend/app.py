import asyncio
import logging
from classes import db
from api import api_bp
from quart import Quart
from quart_cors import cors
from hypercorn.config import Config
from hypercorn.asyncio import serve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 250  # 250MB

config = Config()
config.bind = ["127.0.0.1:5000"]
config.keep_alive_timeout = 3600
config.worker_timeout = 3600

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

if __name__ == "__main__":
    asyncio.run(serve(app, config))
