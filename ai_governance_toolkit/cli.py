"""Console script entry points for pip-installed usage."""
import subprocess
import sys


def serve() -> None:
    """Start the AI Governance Toolkit firewall API (uvicorn on port 8000)."""
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "src.main:app", "--reload", "--port", "8000"],
        check=True,
    )


def dashboard() -> None:
    """Launch the AI Governance compliance dashboard (Streamlit on port 8501)."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "dashboard.py"],
        check=True,
    )
