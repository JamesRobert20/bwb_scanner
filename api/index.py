"""
Vercel serverless function handler for BWB Scanner API.
Uses Mangum to adapt FastAPI (ASGI) to AWS Lambda/Vercel format.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import bwb_scanner
sys.path.insert(0, str(Path(__file__).parent.parent))

from mangum import Mangum
from bwb_scanner.api import app

# Create Mangum handler for Vercel
handler = Mangum(app, lifespan="off")
