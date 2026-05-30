from pathlib import Path
import os


_BACKEND_APP_DIR = Path(__file__).resolve().parents[2] / "app"
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/customerpulse_test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")
__path__ = [str(_BACKEND_APP_DIR)]
