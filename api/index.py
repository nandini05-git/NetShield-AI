import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.join(PARENT_DIR, "backend")

for path in [BACKEND_DIR, PARENT_DIR]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

try:
    from app import app as _backend_app
except ImportError:
    try:
        from backend.app import app as _backend_app
    except Exception as exc:
        import traceback
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        _tb = traceback.format_exc()
        print("CRITICAL BACKEND IMPORT ERROR:\n" + _tb, file=sys.stderr)
        _backend_app = FastAPI(title="NetShield AI Diagnostics")

        @_backend_app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
        async def _diag_handler(path: str):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "NetShield AI Backend Initialization Failed",
                    "exception": str(exc),
                    "traceback": _tb.splitlines(),
                    "sys_path": sys.path[:5]
                }
            )

# Top-level entry points for Vercel Python runtime
app = _backend_app
application = _backend_app
handler = _backend_app




