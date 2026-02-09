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

from typing import Any, Callable, cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


async def view_session(request: Request) -> JSONResponse:
    return JSONResponse({"session": request.session})


async def update_session(request: Request) -> JSONResponse:
    data = await request.json()
    request.session.update(data)

    return JSONResponse({"session": request.session})


SessSetter = Callable[[dict[str, Any]], None]
SessGetter = Callable[[], dict[str, Any]]


def sess_client(client: TestClient) -> tuple[SessSetter, SessGetter]:
    """
    This is an ad-hoc router that expose session management over API, so we can manipulate its content in tests.
    It's not intended to be used beyond integration tests.
    This approach may not be the most conventional, but it's quite reasonable
    if we want to keep using session as
    `request.session` without additional layers of abstraction in a form of a SessionManager.
    """
    router = APIRouter()

    router.add_route("/api/sess/", view_session, methods=["GET"])
    router.add_route("/api/sess/", update_session, methods=["POST"])

    client.app.include_router(router)  # type: ignore[attr-defined]

    def setter(sess: dict[str, Any]) -> None:
        r = client.post("/api/sess/", json=sess)
        r.raise_for_status()

    def getter() -> dict[str, Any]:
        r = client.get("/api/sess/")
        r.raise_for_status()

        return cast(dict[str, Any], r.json()["session"])

    return setter, getter
