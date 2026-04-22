#!/usr/bin/env bash
set -euo pipefail

echo "[Arc-RAR] Linux bootstrap starting"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y curl jq build-essential rustc cargo p7zip-full unrar unzip zip libarchive-tools
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y curl jq gcc gcc-c++ make rust cargo p7zip p7zip-plugins unrar unzip zip bsdtar
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -Sy --needed --noconfirm curl jq base-devel rust cargo p7zip unrar unzip zip libarchive
else
  echo "Unsupported package manager. Install Rust, 7z, tar/libarchive, unzip/zip, and unrar manually."
  exit 1
fi

echo "Done. Verify with: arc-rar backend doctor"
