# Repo Audit

`obi repo-audit` checks whether the core repository foundation files and directories are present from the current working directory.

It is a repository-shape check, not a runtime-core validation pass.

Current checks:
- Cargo workspace manifest
- README
- BUILD_STATUS
- release manifest
- docs directory
- scripts directory
- tests directory
- fixtures directory
- CI workflow file

This report is useful for maintainers picking up the package on a supported machine.
