from __future__ import annotations
import subprocess, sys
subprocess.run([sys.executable, "scripts/build_dataset.py", *sys.argv[1:]], check=True)
