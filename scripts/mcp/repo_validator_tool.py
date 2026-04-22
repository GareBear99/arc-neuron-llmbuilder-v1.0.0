from __future__ import annotations
import subprocess, sys
subprocess.run([sys.executable, "scripts/validate_repo.py", *sys.argv[1:]], check=True)
