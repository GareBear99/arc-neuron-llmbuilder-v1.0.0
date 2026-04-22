# Symlinks, Launchers, and Shell Integration

## Stable binary path doctrine

Preferred install pattern:
- install versioned payload under a product directory
- expose a stable launcher named `arc-rar`
- point shell integrations and scripts at that stable launcher

### Unix-like example
```bash
sudo mkdir -p /opt/arc-rar/0.1.0/bin
sudo ln -sf /opt/arc-rar/0.1.0/bin/arc-rar /usr/local/bin/arc-rar
```

### User-local example
```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/Applications/Arc-RAR/bin/arc-rar" ~/.local/bin/arc-rar
```

### Windows example
- place `arc-rar.exe` in a stable install directory
- add that directory to PATH
- optionally create a small launcher shim if versioned subdirectories are used

## File associations

### macOS
- register document types in the app bundle
- use Launch Services

### Windows
- register through installer / app manifest / registry
- support open-with and context actions like “Extract Here”

### Linux
- install `.desktop` file + MIME associations where supported

## Context actions to aim for
- Open with Arc-RAR
- Extract Here
- Extract to Folder
- Compress to ZIP
- Compress to 7z
