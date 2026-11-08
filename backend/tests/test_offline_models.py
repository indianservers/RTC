import subprocess
import sys
from pathlib import Path


def test_offline_guard_blocks_network():
    script = Path(__file__).resolve().parents[2] / "scripts/offline_guard.py"
    code = (
        "import runpy,socket; guard=runpy.run_path("
        + repr(str(script))
        + "); guard['enforce_offline'](); socket.create_connection(('example.com',443))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert "Offline smoke test blocked network" in result.stderr
