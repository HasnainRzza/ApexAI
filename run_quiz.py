"""Run the APEXAI Quiz Management System (HTML/CSS/JS + Flask API)."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from quiz_system.database.seed import seed
from quiz_system.app import app

if __name__ == "__main__":
    seed()
    print("[APEXAI Quiz] Open http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
