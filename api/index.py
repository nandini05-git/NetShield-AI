import os
import sys
import traceback

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)

# Priority: api/backend (co-located inside function bundle), then root backend
candidate_dirs = [
    os.path.join(CURRENT_DIR, "backend"),
    os.path.join(PARENT_DIR, "backend")
]

for bdir in candidate_dirs:
    if os.path.exists(bdir) and bdir not in sys.path:
        sys.path.insert(0, bdir)

try:
    from app import app, load_ml_model
    from database import init_db_pool
    from mongo_db import init_mongo

    try:
        init_db_pool()
    except Exception as e:
        print(f"Warning: PostgreSQL pool init: {e}")

    try:
        init_mongo()
    except Exception as e:
        print(f"Warning: MongoDB init: {e}")

    try:
        load_ml_model()
    except Exception as e:
        print(f"Warning: ML model load: {e}")

except Exception as exc:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    err_tb = traceback.format_exc()
    print(f"CRITICAL: Failed to import NetShield AI backend:\n{err_tb}")
    app = FastAPI(title="NetShield AI API - Initialization Diagnostic")
    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def diagnostic_fallback(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "ERROR",
                "error": "NetShield AI Serverless Backend Initialization Failed",
                "details": err_tb,
                "current_dir": CURRENT_DIR,
                "sys_path": sys.path[:5]
            }
        )

