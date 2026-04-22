"""CurriculumTrainer — converts curriculum memory signal into model fine-tuning.

The curriculum_memory subsystem has been collecting training signal throughout
every session: which themes succeeded, which failed, what failure clusters
appeared. This data is the right shape for supervised fine-tuning — but
nothing was using it to actually update model weights.

CurriculumTrainer closes this gap by:

  1. Reading curriculum_memory records grouped by theme + failure_cluster
  2. Deciding when enough signal has accumulated to trigger training
  3. Exporting a JSONL training dataset from the signal
  4. Triggering LoRA fine-tuning via transformers/peft (if available)
     or recording a training decision for external execution
  5. Logging every training event to the kernel as a receipt

Fine-tuning strategy:
  - Failure clusters → negative examples (what NOT to do)
  - Success outcomes → positive examples (what TO do)
  - FixNet repair patterns → few-shot correction examples
  - Shadow execution mismatches → contrastive pairs

The model to fine-tune is determined by the active ModelProfile.
If the profile has `training_ready: true` and a `model_path` pointing to
a GGUF or HuggingFace model, training is attempted. Otherwise a training
manifest is written to disk for offline execution.

LoRA adapter (if peft available) is saved alongside the base model and
automatically registered as an overlay profile in ModelProfileStore.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Training decision ─────────────────────────────────────────────────────────

@dataclass
class TrainingDecision:
    """Result of one curriculum training evaluation."""
    should_train: bool
    reason: str
    theme: str
    failure_cluster: str | None
    failure_count: int
    success_count: int
    dataset_path: str | None = None
    adapter_path: str | None = None
    training_status: str = "pending"   # pending | running | complete | failed | deferred
    timestamp: str = field(default_factory=_utcnow)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "kind": "curriculum_training_decision"}


# ── Training example builders ─────────────────────────────────────────────────

def _build_failure_example(record: dict[str, Any]) -> dict[str, Any]:
    """Convert a failure curriculum record to a training negative example."""
    return {
        "role": "system",
        "content": (
            f"You are an AI runtime assistant. "
            f"The following action resulted in a failure outcome. "
            f"Learn to avoid this pattern."
        ),
        "theme": record.get("theme", "unknown"),
        "skill": record.get("skill"),
        "failure_cluster": record.get("failure_cluster"),
        "outcome": "failure",
        "notes": record.get("notes", ""),
        "label": 0,   # negative example
    }


def _build_success_example(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "system",
        "content": (
            f"The following action succeeded. "
            f"Reinforce this pattern."
        ),
        "theme": record.get("theme", "unknown"),
        "skill": record.get("skill"),
        "outcome": "success",
        "notes": record.get("notes", ""),
        "label": 1,   # positive example
    }


def _build_fixnet_example(fix: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "system",
        "content": "When you see this error pattern, apply this solution.",
        "error_type": fix.get("error_type"),
        "error_signature": fix.get("error_signature"),
        "solution": fix.get("solution"),
        "summary": fix.get("summary"),
        "label": 1,
    }


# ── CurriculumTrainer ─────────────────────────────────────────────────────────

class CurriculumTrainer:
    """Converts accumulated curriculum signal into model fine-tuning.

    Args:
        workspace_root: Runtime workspace (training data saved here).
        runtime:        LuciferRuntime for kernel events and fixnet access.
        failure_threshold: Failures in same cluster before training triggers
            (default 5).
        min_examples: Minimum dataset size before training attempt (default 20).
        training_cooldown_s: Min seconds between training runs (default 600).
        export_only: If True, always write dataset to disk but never run
            live training (useful for offline training pipelines, default False).
    """

    def __init__(
        self,
        workspace_root: str | Path,
        runtime: Any = None,
        *,
        failure_threshold: int = 5,
        min_examples: int = 20,
        training_cooldown_s: float = 600.0,
        export_only: bool = False,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.runtime = runtime
        self.failure_threshold = failure_threshold
        self.min_examples = min_examples
        self.training_cooldown_s = training_cooldown_s
        self.export_only = export_only

        self._training_dir = self.workspace_root / ".arc_lucifer" / "training"
        self._training_dir.mkdir(parents=True, exist_ok=True)
        self._last_training_at: float = 0.0
        self._training_history: list[TrainingDecision] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, curriculum_stats: dict[str, Any]) -> TrainingDecision:
        """Decide whether to trigger training based on current curriculum stats.

        Call this from the main loop after each CurriculumMemory update.

        Returns a TrainingDecision — always, even if training is not triggered.
        """
        now = time.monotonic()
        cooldown_remaining = self.training_cooldown_s - (now - self._last_training_at)

        updates = curriculum_stats.get("profiles", []) or []

        # Group by theme + failure_cluster
        clusters: dict[tuple, list[dict]] = {}
        for record in updates:
            theme = record.get("theme", "unknown")
            cluster = record.get("failure_cluster") or "none"
            key = (theme, cluster)
            clusters.setdefault(key, []).append(record)

        # Find the hottest failure cluster
        hot_theme, hot_cluster, hot_failures, hot_successes = "none", None, 0, 0
        for (theme, cluster), records in clusters.items():
            if cluster == "none":
                continue
            failures = sum(1 for r in records if r.get("outcome") == "failure")
            successes = sum(1 for r in records if r.get("outcome") == "success")
            if failures > hot_failures:
                hot_theme, hot_cluster, hot_failures, hot_successes = theme, cluster, failures, successes

        # Decision logic
        if hot_failures < self.failure_threshold:
            return TrainingDecision(
                should_train=False,
                reason=f"failure threshold not met ({hot_failures}/{self.failure_threshold})",
                theme=hot_theme,
                failure_cluster=hot_cluster,
                failure_count=hot_failures,
                success_count=hot_successes,
                training_status="deferred",
            )

        if cooldown_remaining > 0:
            return TrainingDecision(
                should_train=False,
                reason=f"cooldown active ({cooldown_remaining:.0f}s remaining)",
                theme=hot_theme,
                failure_cluster=hot_cluster,
                failure_count=hot_failures,
                success_count=hot_successes,
                training_status="deferred",
            )

        # Build dataset
        dataset = self._build_dataset(updates)
        if len(dataset) < self.min_examples:
            return TrainingDecision(
                should_train=False,
                reason=f"insufficient examples ({len(dataset)}/{self.min_examples})",
                theme=hot_theme,
                failure_cluster=hot_cluster,
                failure_count=hot_failures,
                success_count=hot_successes,
                training_status="deferred",
            )

        # Export dataset
        dataset_path = self._export_dataset(dataset, hot_theme, hot_cluster)

        decision = TrainingDecision(
            should_train=True,
            reason=f"{hot_failures} failures in cluster '{hot_cluster}' exceed threshold {self.failure_threshold}",
            theme=hot_theme,
            failure_cluster=hot_cluster,
            failure_count=hot_failures,
            success_count=hot_successes,
            dataset_path=str(dataset_path),
            training_status="pending",
            evidence={"cluster_records": len(clusters.get((hot_theme, hot_cluster or "none"), []))},
        )

        # Attempt live training
        if not self.export_only:
            decision = self._attempt_lora_training(decision, dataset_path)
        else:
            decision.training_status = "exported_for_offline"

        self._last_training_at = time.monotonic()
        self._training_history.append(decision)
        self._emit_kernel_event(decision)
        return decision

    def export_fixnet_training_data(self) -> Path | None:
        """Export FixNet repair patterns as few-shot training examples."""
        if not self.runtime:
            return None
        try:
            stats = self.runtime.fixnet_stats()
            cases = stats.get("cases", [])
        except Exception:
            return None

        if not cases:
            return None

        examples = [_build_fixnet_example(c) for c in cases]
        path = self._training_dir / f"fixnet_examples_{_utcnow()[:10]}.jsonl"
        with open(path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        return path

    def training_manifest(self) -> dict[str, Any]:
        """Write a training manifest for offline/external fine-tuning pipelines."""
        manifest = {
            "generated_at": _utcnow(),
            "workspace": str(self.workspace_root),
            "training_dir": str(self._training_dir),
            "history": [d.to_dict() for d in self._training_history[-20:]],
            "instructions": (
                "Run LoRA fine-tuning on the exported JSONL datasets. "
                "Recommended: use `transformers` + `peft` with LoRA rank=8, "
                "alpha=16, target_modules=['q_proj','v_proj']. "
                "Save adapter to training_dir/lora_adapter_<theme>/. "
                "Register with ModelProfileStore as an overlay profile."
            ),
        }
        manifest_path = self._training_dir / "training_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def status(self) -> dict[str, Any]:
        return {
            "training_history_count": len(self._training_history),
            "last_training_at": (
                _utcnow() if self._last_training_at == 0.0
                else datetime.fromtimestamp(
                    time.time() - (time.monotonic() - self._last_training_at),
                    tz=timezone.utc,
                ).isoformat()
            ),
            "cooldown_remaining_s": max(
                0, self.training_cooldown_s - (time.monotonic() - self._last_training_at)
            ),
            "recent_decisions": [d.to_dict() for d in self._training_history[-5:]],
            "training_dir": str(self._training_dir),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_dataset(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        examples = []
        for r in records:
            if r.get("outcome") == "failure":
                examples.append(_build_failure_example(r))
            elif r.get("outcome") == "success":
                examples.append(_build_success_example(r))
        return examples

    def _export_dataset(
        self,
        examples: list[dict[str, Any]],
        theme: str,
        cluster: str | None,
    ) -> Path:
        safe_theme = theme.replace("/", "_")[:40]
        safe_cluster = (cluster or "none").replace("/", "_")[:40]
        filename = f"dataset_{safe_theme}_{safe_cluster}_{_utcnow()[:10]}.jsonl"
        path = self._training_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        return path

    def _attempt_lora_training(
        self, decision: TrainingDecision, dataset_path: Path
    ) -> TrainingDecision:
        """Attempt live LoRA fine-tuning if transformers + peft available."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer  # type: ignore
            from peft import LoraConfig, get_peft_model  # type: ignore
        except ImportError:
            decision.training_status = "deferred_no_peft"
            decision.reason += " (peft/transformers not installed — dataset exported for offline training)"
            return decision

        # Check for trainable model profile
        active_profile = None
        if self.runtime:
            try:
                from model_services.profiles import ModelProfileStore
                store = ModelProfileStore(self.workspace_root / ".arc_lucifer" / "model_profiles")
                active_profile = store.active_profile()
            except Exception:
                pass

        if not active_profile or not active_profile.get("training_ready"):
            decision.training_status = "deferred_no_trainable_model"
            decision.reason += " (no training_ready model profile — dataset exported)"
            return decision

        model_path = active_profile.get("model_path") or active_profile.get("hf_model_id")
        if not model_path:
            decision.training_status = "deferred_no_model_path"
            return decision

        try:
            # Load model + tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)

            # Apply LoRA
            lora_config = LoraConfig(
                r=8,
                lora_alpha=16,
                target_modules=["q_proj", "v_proj"],
                lora_dropout=0.05,
                bias="none",
                task_type="CAUSAL_LM",
            )
            model = get_peft_model(model, lora_config)

            # Build HuggingFace dataset from JSONL
            from datasets import load_dataset  # type: ignore
            dataset = load_dataset("json", data_files=str(dataset_path), split="train")

            adapter_dir = self._training_dir / f"lora_{decision.theme}_{_utcnow()[:10]}"
            adapter_dir.mkdir(parents=True, exist_ok=True)

            training_args = TrainingArguments(
                output_dir=str(adapter_dir),
                num_train_epochs=1,
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                save_steps=50,
                logging_steps=10,
                learning_rate=2e-4,
                fp16=True,
                report_to="none",
            )
            trainer = Trainer(model=model, args=training_args, train_dataset=dataset)
            trainer.train()
            model.save_pretrained(str(adapter_dir))

            decision.adapter_path = str(adapter_dir)
            decision.training_status = "complete"

            # Register adapter as model profile overlay
            if self.runtime:
                try:
                    from model_services.profiles import ModelProfileStore
                    store = ModelProfileStore(self.workspace_root / ".arc_lucifer" / "model_profiles")
                    store.register_profile(
                        f"lora_{decision.theme}",
                        {
                            "backend_type": "lora_adapter",
                            "base_model": model_path,
                            "adapter_path": str(adapter_dir),
                            "training_theme": decision.theme,
                            "failure_cluster": decision.failure_cluster,
                            "trained_at": _utcnow(),
                            "training_ready": False,
                            "notes": f"LoRA adapter trained on {decision.failure_count} failure examples",
                        },
                    )
                except Exception:
                    pass

        except Exception as exc:
            decision.training_status = f"failed: {exc}"

        return decision

    def _emit_kernel_event(self, decision: TrainingDecision) -> None:
        if not self.runtime:
            return
        kernel = getattr(self.runtime, "kernel", None)
        if kernel:
            try:
                kernel.record_evaluation("curriculum_trainer", decision.to_dict())
            except Exception:
                pass
