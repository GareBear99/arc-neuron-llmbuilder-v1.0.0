from __future__ import annotations
import subprocess, sys
subprocess.run([sys.executable, "scripts/build_repo_capsule.py", *sys.argv[1:]], check=True)
