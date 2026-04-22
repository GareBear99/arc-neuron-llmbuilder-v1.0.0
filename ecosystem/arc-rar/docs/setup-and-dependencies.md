# Setup and dependencies

## Backend tools

Arc-RAR relies on host archive tools. Install as many as are practical:

### macOS
- `brew install p7zip`
- `brew install unzip zip`
- `brew install libarchive`

### Ubuntu / Debian
- `sudo apt install p7zip-full unzip zip tar libarchive-tools unrar`

### Fedora
- `sudo dnf install p7zip p7zip-plugins unzip zip tar bsdtar unrar`

### Arch
- `sudo pacman -S p7zip unzip zip tar libarchive unrar`

### Windows
- install 7-Zip
- install WinRAR or UnRAR if desired for RAR extraction
- ensure tools are on PATH when using the CLI backend strategy

## Rust toolchain

- install Rust/Cargo on the build machine
- this environment did not include `cargo`, so compile validation was not performed here

## Config bootstrap

```bash
arc-rar config init
arc-rar backend doctor
```


## Validation note

This pack was assembled without a live Cargo toolchain in the execution environment used to package it, so build commands are documented but not claimed as validated inside this container. Validate on target hosts before release.
