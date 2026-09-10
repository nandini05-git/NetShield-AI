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

from app import app


