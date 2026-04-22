# Release Process

1. Update version in workspace crates.
2. Update CHANGELOG.
3. Run `scripts/verify-repo.sh`.
4. Run `scripts/smoke.sh` on a supported machine.
5. Update compatibility matrix and production gaps.
6. Create versioned archive.
7. Publish release notes with truth boundaries.

Never label a release production-ready unless the real execution core exists and is validated.
