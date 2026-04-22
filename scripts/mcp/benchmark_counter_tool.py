from __future__ import annotations
import subprocess, sys
subprocess.run([sys.executable, "scripts/run_benchmarks.py", *sys.argv[1:]], check=True)
