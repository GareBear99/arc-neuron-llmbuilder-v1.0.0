# Windows installer notes

Use MSIX, WiX, or Inno Setup after the WinUI app is real.

Checklist:
- install CLI binary to a stable path
- add PATH entry only if user opts in
- register file associations via installer, not ad-hoc at runtime
- add Start Menu entry for native GUI app
- preserve receipt/config directories across upgrades
- avoid machine-wide registry writes unless elevated installer mode is selected
