import os, logging, asyncio
from modal import App, Image, Secret, asgi_app
from quart import Quart, request, jsonify
from quart_cors import cors

quart_app = Quart(__name__)
quart_app = cors(
    quart_app,
    allow_origin="*",
    allow_headers="*",
    allow_methods=["POST", "DELETE"]
)

app = App(name="modu-backend")

image = (
    Image.debian_slim()
    .pip_install_from_requirements("requirements.txt")
)

@app.function(
    image=image,
    secrets=[Secret.from_name("modu-backend-secrets")]
)
@asgi_app()
def quart_asgi_app():
    return quart_app


@app.local_entrypoint()
def serve():
    quart_app.run()
