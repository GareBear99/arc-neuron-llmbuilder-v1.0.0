$ErrorActionPreference = "Stop"
Write-Host "[Arc-RAR] Windows bootstrap starting"
if (Get-Command winget -ErrorAction SilentlyContinue) {
  winget install -e --id Rustlang.Rustup
  winget install -e --id 7zip.7zip
  winget install -e --id RARLab.WinRAR
} else {
  Write-Host "winget not found. Install Rustup, 7-Zip, and optionally WinRAR/UnRAR manually."
  exit 1
}
Write-Host "Done. Verify with: arc-rar backend doctor"
