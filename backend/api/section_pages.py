import logging, datetime
from classes import S3Bucket
from quart import Blueprint, jsonify
from functions import section_pages_detection as detect_section_pages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

section_pages_bp = Blueprint("section_pages", __name__)

@section_pages_bp.route("/<string:spec_id>", methods=["GET"])
async def section_pages(spec_id: str):

    start_time = datetime.datetime.now()

    s3 = S3Bucket()
    async with s3.s3_client() as s3_client:
        section_page_dict = await detect_section_pages(spec_id, s3, s3_client)

    return jsonify({
        "section_pages": section_page_dict,
        "run_time": f"{datetime.datetime.now() - start_time}"
    }), 200
