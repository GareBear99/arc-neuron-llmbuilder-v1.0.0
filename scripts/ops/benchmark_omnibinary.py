#!/usr/bin/env python3
"""scripts/ops/benchmark_omnibinary.py — Hard performance benchmark for Omnibinary store."""
from __future__ import annotations
import argparse, json, statistics, tempfile, time, sys
from pathlib import Path
from uuid import uuid4
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime.learning_spine import LearningEvent, OmnibinaryStore, sha256_file

def make_event(n):
    return LearningEvent(ts_utc=1700000000+n, source="benchmark", event_type="bench_event",
                         payload={"n": n, "data": "x"*200}, event_id=uuid4().hex)

def run_benchmark(n_events=1000, flush_every=50):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bench.obin"
        store = OmnibinaryStore(path, index_flush_every=flush_every)
        events = [make_event(i) for i in range(n_events)]

        t0 = time.perf_counter()
        ids = [store.append(ev) for ev in events]
        store.flush()
        append_time = time.perf_counter() - t0
        file_size = path.stat().st_size

        for eid in ids[:10]: store.get(eid)  # warmup
        latencies = []
        for eid in ids:
            t = time.perf_counter()
            ev = store.get(eid)
            latencies.append((time.perf_counter()-t)*1000)
            assert ev is not None

        t1 = time.perf_counter()
        scanned = list(store.scan())
        scan_time = time.perf_counter() - t1
        assert len(scanned) == n_events

        idx_path = path.with_suffix(path.suffix+".idx")
        idx_path.unlink(missing_ok=True)
        store2 = OmnibinaryStore(path, index_flush_every=flush_every)
        t2 = time.perf_counter()
        verify = store2.verify()
        verify_time = time.perf_counter() - t2

        sha_before = sha256_file(path)
        store3 = OmnibinaryStore(path)
        fidelity = all(store3.get(eid) is not None for eid in ids[:20])

        return {
            "n_events": n_events, "flush_every": flush_every,
            "append":   {"total_ms": round(append_time*1000,2), "events_per_sec": round(n_events/append_time)},
            "lookup_o1":{"events_per_sec": round(n_events/(sum(latencies)/1000)),
                         "p50_ms": round(statistics.median(latencies),4),
                         "p95_ms": round(sorted(latencies)[int(n_events*.95)],4),
                         "p99_ms": round(sorted(latencies)[int(n_events*.99)],4)},
            "scan":     {"total_ms": round(scan_time*1000,2)},
            "rebuild":  {"total_ms": round(verify_time*1000,2), "events": verify["event_count"]},
            "storage":  {"file_bytes": file_size, "bytes_per_event": round(file_size/n_events)},
            "fidelity": {"sha256_stable": sha256_file(path)==sha_before, "spot_check": fidelity},
        }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=1000)
    ap.add_argument("--flush-every", type=int, default=50)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    results = run_benchmark(args.events, args.flush_every)
    print(f"\nOmnibinary Benchmark — {args.events} events")
    print(f"  Append:   {results['append']['events_per_sec']:,} events/sec  ({results['append']['total_ms']}ms)")
    print(f"  O(1) Get: {results['lookup_o1']['events_per_sec']:,} lookups/sec  p50={results['lookup_o1']['p50_ms']}ms  p99={results['lookup_o1']['p99_ms']}ms")
    print(f"  Scan:     {results['scan']['total_ms']}ms total")
    print(f"  Rebuild:  {results['rebuild']['total_ms']}ms for {results['rebuild']['events']} events")
    print(f"  Storage:  {results['storage']['bytes_per_event']} bytes/event")
    print(f"  Fidelity: SHA256_stable={results['fidelity']['sha256_stable']}  spot={results['fidelity']['spot_check']}")
    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"  Written: {args.output}")
    print(json.dumps({"ok": True, **results}))

if __name__ == "__main__":
    main()
