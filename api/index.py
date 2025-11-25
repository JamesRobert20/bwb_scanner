import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bwb_scanner.api import app

app = app
