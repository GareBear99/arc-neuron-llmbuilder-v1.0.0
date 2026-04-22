# Arc-RAR completion checklist

## Implemented in this pack
- Host-tool-backed archive list/info/extract/create/test flow
- Signature-aware format sniffing with extension fallback
- Autowrap intent validation across archive/gui/api/automation planes
- Receipt persistence to disk
- Config path resolution and directory bootstrap
- File-based GUI IPC bridge
- GUI daemon processing loop with status, response, and event files
- Backend doctor inventory
- Packaging and setup templates

## Still required before an honest production claim
- Fully implemented macOS native app
- Fully implemented Windows native app
- Fully implemented Linux native app
- Build/test validation on actual target OSes
- Signed and installer-verified release pipeline
- More fixture archives and backend regression tests
- Named-pipe / Unix-socket transport in addition to file IPC
