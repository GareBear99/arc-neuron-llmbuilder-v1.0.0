# Production Readiness Checklist

## Repository hygiene
- License present
- Security policy present
- CI workflow present
- Changelog present
- Contributing guide present
- Issue and PR templates present

## Engineering validation
- `cargo fmt --check`
- `cargo check`
- `cargo test`
- representative smoke scripts on supported hosts
- cache/index roundtrip validation

## Runtime milestones still required
- one real guest decoder
- one real canonical lowering path
- one real Cranelift-emitted host block
- translated block cache reuse and invalidation
- syscall personality mediation
- sandbox / broker process isolation

## Release quality
- versioned artifacts
- signed releases
- compatibility matrix updated
- production gaps updated honestly
