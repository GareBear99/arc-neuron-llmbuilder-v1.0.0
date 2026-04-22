# Benchmarking Strategy

## Goal
Measure real progress instead of inferring performance from architecture alone.

## Early metrics
- inspect latency
- plan latency
- lower-preview latency
- decode-preview latency
- dispatch-preview latency
- native launch overhead
- cache hit/miss ratios

## Future metrics
- translated block compile latency
- translated block reuse rate
- steady-state throughput for repeated CLI workloads
- syscall mediation overhead
- invalidation frequency for self-modifying code cases

## Reporting
Store benchmark outputs under `artifacts/bench/` in CI or local runs.
