import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

for bdir in [
    os.path.join(CURRENT_DIR, "backend"),
    os.path.join(PARENT_DIR, "backend")
]:
    if os.path.exists(bdir) and bdir not in sys.path:
        sys.path.insert(0, bdir)

import traceback

try:
    from app import app
except Exception as exc:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    tb = traceback.format_exc()
    print("CRITICAL BACKEND IMPORT ERROR:\n" + tb, file=sys.stderr)

    app = FastAPI(title="NetShield AI Diagnostics")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def diagnostic_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "NetShield AI Backend Initialization Failed",
                "exception": str(exc),
                "traceback": tb.splitlines(),
                "sys_path": sys.path[:5],
                "files_in_backend": os.listdir(os.path.join(PARENT_DIR, "backend")) if os.path.exists(os.path.join(PARENT_DIR, "backend")) else []
            }
        )


