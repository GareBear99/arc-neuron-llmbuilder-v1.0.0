from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "arc_neuron_nextgen"
OUT.mkdir(parents=True, exist_ok=True)

ARTIFACTS = {
    "gguf": ROOT / "artifacts" / "gguf" / "ARC-Neuron-Tiny-Integrated-0.07M-v0.2-F32.gguf",
    "ancf": ROOT / "artifacts" / "ancf" / "ARC-Neuron-Tiny-Integrated-0.07M-v0.2.ancf",
    "model_card": ROOT / "artifacts" / "gguf" / "ARC-Neuron-Tiny-Integrated-0.07M-v0.2.modelcard.json",
    "omnibinary_ledger": ROOT / "artifacts" / "omnibinary" / "arc-neuron-learning-ledger.obin",
    "arc_rar_bundle": ROOT / "artifacts" / "archives" / "arc-neuron-integrated-demo.arcrar.zip",
    "base_prep_ledger": ROOT / "artifacts" / "omnibinary" / "arc-neuron-base-prep-ledger.obin",
    "base_release_ledger": ROOT / "artifacts" / "omnibinary" / "arc-neuron-base-release-prep-ledger.obin",
}

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

manifest = {
    "family": "ARC-Neuron",
    "state": "tiny_regression_floor_with_base_release_contract",
    "canonical_artifact": "ANCF",
    "deploy_artifact": "GGUF",
    "stronger_external_checkpoint_required": True,
    "artifacts": {},
}
for name, path in ARTIFACTS.items():
    manifest["artifacts"][name] = {
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path) if path.exists() else None,
    }

manifest_path = OUT / "arc_neuron_release_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
status = {
    "ok": all(v["exists"] for v in manifest["artifacts"].values()),
    "release_manifest": str(manifest_path.relative_to(ROOT)),
    "next_action": "Provide stronger external checkpoint and execute ARC-Neuron Base promotion path."
}
(OUT / "arc_neuron_nextgen_ready.json").write_text(json.dumps(status, indent=2), encoding='utf-8')
print(json.dumps(status, indent=2))
