# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import os
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from core.telemetry import configure_uvicorn_logging, init_logging
from datarobot_asgi_middleware import DataRobotASGIMiddleware
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api import router as api_router
from app.config import Config
from app.deps import Deps, create_deps

base_router = APIRouter()

base_router.include_router(api_router)

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
STATIC_DIR = ROOT_DIR / "static"
NOTEBOOK_ID = os.getenv("NOTEBOOK_ID", "")

templates = Jinja2Templates(directory=ROOT_DIR / "templates")

warnings.filterwarnings("ignore")


@base_router.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint for Kubernetes probes.

    If you don't want this, delete `use_health=True` in the middleware.
    """
    return {"status": "healthy"}


def register_log_filter() -> None:
    """
    Removes logs from healthiness/readiness endpoints so they don't spam
    and pollute application log flow
    """

    class EndpointFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return (
                record.args  # type: ignore[return-value]
                and len(record.args) >= 3
                and record.args[2] != "/health"  # type: ignore[index]
            )

    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


def get_app_base_url(api_port: str | None) -> str:
    """Get and normalize the application base URL."""
    app_base_url = os.getenv("BASE_PATH", "")
    notebook_id = os.getenv("NOTEBOOK_ID", "")
    if not app_base_url and notebook_id:
        if api_port:
            app_base_url = f"notebook-sessions/{notebook_id}/ports/{api_port}"
        else:
            app_base_url = f"notebook-sessions/{notebook_id}"

    if app_base_url:
        return "/" + app_base_url.strip("/") + "/"
    else:
        return "/"


def get_manifest_assets(
    manifest_path: Path, entry: str = "index.html", app_base_url: str = "/"
) -> dict[str, list[str]]:
    """
    Reads the Vite manifest and returns the JS and CSS files for the given entry.
    """
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    entry_data = manifest.get(entry, {})
    js_files = []
    css_files = []

    # Main JS file
    if "file" in entry_data:
        js_files.append(app_base_url + entry_data["file"])

    # CSS files
    for css in entry_data.get("css", []):
        css_files.append(app_base_url + css)

    return {"js": js_files, "css": css_files}


def create_app(
    title: str = "Agentic Application Starter",
    config: Config | None = None,
    deps: Deps | None = None,
) -> FastAPI:
    """
    Create the FastAPI app setup with all the middleware and routers.
    """
    if config is None:
        config = Config()

    init_logging(level=config.log_level, format_type=config.log_format)

    configure_uvicorn_logging(
        log_format=config.log_format, log_level=config.log_level.value
    )

    logger.info("App is starting up.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        async with create_deps(config, deps) as dependencies:
            app.state.deps = dependencies
            yield

    app = FastAPI(title=title, lifespan=lifespan)

    # Add our middleware for DataRobot Custom Applications
    app.add_middleware(DataRobotASGIMiddleware, health_endpoint="/health")

    # Generate a unique session cookie name based on config or app's base path
    if config.session_cookie_name != "sess":
        # Use the configured cookie name if it's been customized
        session_cookie_name = config.session_cookie_name
    else:
        # Auto-generate based on base path to avoid conflicts between apps
        cookie_path = get_app_base_url(None)
        # Create a safe cookie name from the base path
        cookie_suffix = (
            cookie_path.strip("/").replace("/", "_").replace("-", "_") or "default"
        )
        session_cookie_name = f"sess_{cookie_suffix}"

    app.add_middleware(
        SessionMiddleware,
        session_cookie=session_cookie_name,
        secret_key=config.session_secret_key,
        max_age=config.session_max_age,
        https_only=config.session_https_only,
        path=cookie_path,
    )

    app.include_router(base_router)

    # This is the base path for the app, used to serve static files and templates
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="static",
    )

    # This is the final path that serves the React app
    @app.get("{full_path:path}")
    async def serve_root(request: Request) -> HTMLResponse:
        """
        Serve the React index.html for the all routes, injecting ENV variables and fixing asset paths.
        """
        manifest_path = STATIC_DIR / ".vite" / "manifest.json"

        api_port = os.getenv("PORT", "8080")
        app_base_url = get_app_base_url(api_port)

        env_vars = {
            "BASE_PATH": app_base_url,
            "API_PORT": api_port,
            "DATAROBOT_ENDPOINT": os.getenv("DATAROBOT_ENDPOINT", ""),
        }

        manifest_assets = get_manifest_assets(
            manifest_path,
            "index.html",
            app_base_url,
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "env": env_vars,
                "app_base_url": app_base_url,
                "js_files": manifest_assets["js"],
                "css_files": manifest_assets["css"],
            },
        )

    register_log_filter()

    return app
