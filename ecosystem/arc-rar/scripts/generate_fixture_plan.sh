#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
Arc-RAR fixture generation plan:
1. Create safe sample directories with unicode, nested paths, and empty folders.
2. Generate zip/tar/tar.gz/7z fixtures from those samples.
3. Add at least one encrypted zip and one encrypted 7z.
4. Add a malicious path traversal fixture for extraction rejection tests.
5. Add a corrupted fixture per format to validate test/info failure modes.
EOF
