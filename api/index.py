import os
import sys

# Add backend directory to sys.path so modules (config, database, mongo_db, routes) load cleanly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, load_ml_model
from database import init_db_pool
from mongo_db import init_mongo

# Eagerly initialize DB pools and ML model on serverless worker spin-up
try:
    init_db_pool()
except Exception:
    pass

try:
    init_mongo()
except Exception:
    pass

try:
    load_ml_model()
except Exception:
    pass
