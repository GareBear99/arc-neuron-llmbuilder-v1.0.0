#!/usr/bin/env python3
"""scripts/ops/bootstrap_keys.py — Generate runtime secrets after a fresh clone.

SECURITY CONTRACT
─────────────────
Private key files are in .gitignore and must NEVER be committed.
This script is the single source of truth for how they are created.
Run it once after cloning (or after rotating keys):

    python3 scripts/ops/bootstrap_keys.py

It is idempotent: if a key already exists it will not overwrite it unless
--force is passed.

Key inventory
─────────────
  ecosystem/arc-core/ARC_Console/data/keys/receipt_signing.key
      32-byte HMAC-SHA256 secret used to sign tamper-evident audit receipts.
      Format: hex-encoded on a single line (64 hex chars + newline).
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

KEYS: list[dict] = [
    {
        "path": ROOT / "ecosystem" / "arc-core" / "ARC_Console" / "data" / "keys" / "receipt_signing.key",
        "description": "HMAC-SHA256 receipt signing secret (32 bytes, hex-encoded)",
        "generate": lambda: secrets.token_hex(32),
    },
]

GITKEEP = ROOT / "ecosystem" / "arc-core" / "ARC_Console" / "data" / "keys" / ".gitkeep"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate runtime secrets for ARC-Core.")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing keys (triggers key rotation — invalidates signed receipts).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing anything.",
    )
    args = ap.parse_args()

    results: list[dict] = []

    for key_spec in KEYS:
        path: Path = key_spec["path"]
        path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure .gitkeep exists so the directory is tracked by git even when
        # the actual key files are gitignored.
        if not GITKEEP.exists() and not args.dry_run:
            GITKEEP.touch()

        if path.exists() and not args.force:
            results.append({"path": str(path.relative_to(ROOT)), "action": "skipped (already exists)"})
            continue

        action = "would generate" if args.dry_run else "generated"
        if not args.dry_run:
            value = key_spec["generate"]()
            path.write_text(value + "\n", encoding="utf-8")
            # Restrict permissions: owner-read-only on Unix systems.
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass  # Windows does not support chmod in the same way

        results.append({
            "path": str(path.relative_to(ROOT)),
            "description": key_spec["description"],
            "action": action,
        })

    for r in results:
        status = "✓" if "generated" in r["action"] else ("⊘" if "skip" in r["action"] else "○")
        print(f"  {status}  {r['action']:30s}  {r['path']}")

    if args.dry_run:
        print("\n[dry-run] No files were written.")
    else:
        skipped = sum(1 for r in results if "skip" in r["action"])
        generated = len(results) - skipped
        print(f"\n  {generated} key(s) generated, {skipped} skipped.")
        if generated:
            print("  ⚠  Keep these files secret. They are in .gitignore and will not be committed.")


if __name__ == "__main__":
    main()
