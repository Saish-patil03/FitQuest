import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("backend", remote_path="/root/backend")
)

app = modal.App("fitquest-backend")

@app.function(image=image)
@modal.asgi_app()
def serve():
    from backend.main import app as web_app
    return web_app