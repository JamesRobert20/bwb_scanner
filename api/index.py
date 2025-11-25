import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the FastAPI app - Vercel handles ASGI natively
from bwb_scanner.api import app

# Vercel expects the app to be exported directly (not wrapped in Mangum)
# The variable name must be 'app' for Vercel's ASGI handler
app = app
