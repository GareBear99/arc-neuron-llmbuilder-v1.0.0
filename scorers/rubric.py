"""scorers/rubric.py — Task-aware capability scorer for ARC-Neuron benchmarks."""
from __future__ import annotations
from typing import Any

def _is_substantial(text: str, min_chars: int = 60) -> bool:
    return len(text.strip()) >= min_chars

def _contains_any(text: str, options: list[str]) -> bool:
    lowered = text.lower()
    return any(option in lowered for option in options)

def _score_parts(text: str, checks: list[tuple[str, bool]]) -> tuple[int, list[str]]:
    passed = [name for name, ok in checks if ok]
    return len(passed), passed

def _score_retention(text: str, task: dict) -> dict[str, Any]:
    lowered = text.lower()
    checks = [
        ("responds_to_prompt",    len(text.strip()) >= 40),
        ("no_hallucinated_prior", not _contains_any(lowered, ["as we discussed earlier","you mentioned that","in our previous session","you told me"])),
        ("bounded_confidence",    _contains_any(lowered, ["based on","given","from what","according to","as stated","the constraint","as defined"]) or _is_substantial(text)),
        ("preserves_goal",        _contains_any(lowered, ["goal","objective","aim","purpose","target","mission"])),
        ("preserves_constraint",  _contains_any(lowered, ["constraint","must not","cannot","requirement","rule","preserve","must","should not"])),
        ("names_next_action",     _contains_any(lowered, ["next","action","step","should","check","verify","validate","recommend"])),
    ]
    raw, matched = _score_parts(lowered, checks)
    return {"raw_score": raw, "normalized_score": round(raw/max(1,len(checks)),4),
            "capability": task.get("capability","continuity"),
            "notes": f"Retention: {raw}/{len(checks)} checks passed.",
            "matched_checks": matched, "scoring_mode": "retention"}

def score_record(output_text: str, task: dict | None = None) -> dict[str, Any]:
    text       = (output_text or "").strip()
    lowered    = text.lower()
    capability = (task or {}).get("capability", "generic")
    scoring_mode = (task or {}).get("scoring", "rubric")
    raw_ref = (task or {}).get("reference", {})
    if not isinstance(raw_ref, dict):
        raw_ref = {"rubric": str(raw_ref)} if raw_ref else {}
    reference = raw_ref
    if not text:
        return {"raw_score":0,"normalized_score":0.0,"capability":capability,"notes":"Empty output","matched_checks":[]}
    if scoring_mode == "retention" and task:
        return _score_retention(text, task)
    notes: list[str] = []
    common = [
        ("mentions_constraints",            _contains_any(lowered,["constraint","preserve","boundary","interface"])),
        ("mentions_risk_or_tradeoff",       _contains_any(lowered,["risk","tradeoff","regression","failure mode"])),
        ("mentions_validation_or_evidence", _contains_any(lowered,["validate","test","evidence","verify","observability"])),
    ]
    caps: dict[str, list[tuple[str,bool]]] = {
        "planning":             [("has_ordered_plan",_contains_any(lowered,["plan","steps","first","then"])),("prefers_narrow_change",_contains_any(lowered,["smallest","minimal","targeted","narrow"])),("preserves_interfaces",_contains_any(lowered,["preserve interfaces","public api","boundary","without breaking"]))],
        "reasoning":            [("separates_fact_from_inference",_contains_any(lowered,["fact","inference","given","unknown"])),("rejects_or_bounds_unsafe_change",_contains_any(lowered,["reject","not acceptable","only if","conditionally"])),("mentions_conflict",_contains_any(lowered,["conflict","contradiction","tradeoff","threatens"]))],
        "critique":             [("identifies_missing_evidence",_contains_any(lowered,["missing evidence","not shown","unverified","assumption"])),("identifies_scope_risk",_contains_any(lowered,["too broad","scope","blast radius","regression"])),("proposes_followup_check",_contains_any(lowered,["validate","test","verify","instrument"]))],
        "repair":               [("offers_specific_fix",_contains_any(lowered,["patch","fix","change","guard","rollback"])),("keeps_fix_small",_contains_any(lowered,["minimal","targeted","surgical","narrow"])),("adds_regression_protection",_contains_any(lowered,["test","regression","validate","assert"]))],
        "compression":          [("preserves_goal",_contains_any(lowered,["goal","objective","task"])),("preserves_blockers",_contains_any(lowered,["blocker","risk","constraint"])),("preserves_next_action",_contains_any(lowered,["next","action","do this","follow-up"]))],
        "calibration":          [("states_uncertainty",_contains_any(lowered,["likely","uncertain","confidence","may","bounded"])),("avoids_false_certainty",_is_substantial(text) and not _contains_any(lowered,["definitely","certainly","guaranteed"])),("ties_claims_to_evidence",_contains_any(lowered,["evidence","based on","from the prompt","given only"]))],
        "paraphrase_stability": [("preserves_meaning",_contains_any(lowered,["same meaning","preserve","equivalent","without changing"])),("mentions_constraints",_contains_any(lowered,["constraint","key point","do not lose"])),("avoids_additional_claims",_is_substantial(text) and not _contains_any(lowered,["new requirement","extra guarantee","additional promise"]))],
        "quantization_retention":[("mentions_core_behavior",_contains_any(lowered,["retain","preserve","behavior","quality"])),("compares_variants",_contains_any(lowered,["full precision","quantized","gguf","variant"])),("mentions_regression_threshold",_contains_any(lowered,["threshold","regression","drop","retention"]))],
        "continuity":           [("preserves_thread",_contains_any(lowered,["goal","objective","prior","earlier","we agreed","session"])),("preserves_constraint",_contains_any(lowered,["constraint","rule","must","requirement"])),("names_next_action",_contains_any(lowered,["next","action","step","check","verify"]))],
        "reflection":           [("identifies_issue",_contains_any(lowered,["overclaim","wrong","incorrect","contradiction","redundant","too broad"])),("revises_or_corrects",_contains_any(lowered,["revise","correct","instead","more accurately","better to say","rephrase"])),("bounded_final",_contains_any(lowered,["likely","bounded","based on","evidence","uncertain","confidence"]))],
        "lexical_accuracy":     [("uses_canonical_source",_contains_any(lowered,["module","canonical","stored","retrieve","source","known"])),("avoids_hallucination",_contains_any(lowered,["not supported","unknown","not in","no evidence","cannot confirm"])),("bounded_response",_contains_any(lowered,["based on","from the","as defined","according to"]))],
        "archive_reasoning":    [("mentions_archive_layer",_contains_any(lowered,["archive","bundle","arc-rar","omnibinary","ledger"])),("mentions_rollback",_contains_any(lowered,["rollback","restore","replay","prior state"])),("mentions_lineage",_contains_any(lowered,["lineage","receipt","trace","provenance","evidence"]))],
        "runtime_reasoning":    [("mentions_runtime_layer",_contains_any(lowered,["runtime","adapter","backend","model","inference"])),("mentions_timeout_or_guard",_contains_any(lowered,["timeout","guard","limit","boundary","safety"])),("evidence_based",_contains_any(lowered,["evidence","based on","from the","receipt"]))],
        "state_evidence":       [("names_state_element",_contains_any(lowered,["state","incumbent","scoreboard","floor","score"])),("links_to_evidence",_contains_any(lowered,["receipt","report","benchmark","evidence","proof"])),("proposes_action",_contains_any(lowered,["next","should","action","verify","check"]))],
        "system_spine_reasoning":[("names_spine_component",_contains_any(lowered,["language module","omnibinary","arc-rar","runtime","cognition core"])),("describes_role",_contains_any(lowered,["truth","memory","archive","govern","promote","train"])),("coherent_relationship",_contains_any(lowered,["feeds","into","produces","enables","provides","supports"]))],
        "native_operation_planning":[("names_operation",_contains_any(lowered,["train","benchmark","promote","bundle","export","verify"])),("orders_steps",_contains_any(lowered,["first","then","next","after","before","finally"])),("names_gate",_contains_any(lowered,["gate","check","validate","floor","threshold","pass"]))],
        "deterministic_compliance":[("follows_format",_contains_any(lowered,["json","yaml","output","format","structure"])),("bounded",_contains_any(lowered,["bounded","constraint","rule","requirement"])),("evidence",_contains_any(lowered,["evidence","based on","given"]))],
        "deterministic_format":  [("structured_output",_contains_any(lowered,["json","yaml","list","format","structure","output"])),("no_hallucination",not _contains_any(lowered,["i think","perhaps","maybe","probably"])),("complete",_contains_any(lowered,["complete","all","every","each"]))],
        "refusal_correctness":   [("identifies_refusal_case",_contains_any(lowered,["cannot","refuse","not able","outside","scope","boundary"])),("explains_reason",_contains_any(lowered,["because","reason","constraint","policy","doctrine"])),("offers_alternative",_contains_any(lowered,["instead","alternative","suggest","can help with","within"]))],
        "english_understanding": [
            ("produces_coherent_response",  len(text.strip()) >= 20),
            ("addresses_question_directly",  not text.strip().startswith("I")),
            ("shows_comprehension",         _contains_any(lowered,["means","refers to","is","states","indicates","the claim","the sentence","this says","this means","in other words","simply put","restate","paraphrase","it is","they are"])),
        ],
        "instruction_following": [
            ("follows_format",           _contains_any(lowered,["1.","2.","3.","first:","second:","third:","problem:","action:","result:","agree","disagree"])),
            ("stays_on_task",            _is_substantial(text) and not _contains_any(lowered,["i cannot do","i am not able to","as an ai"])),
            ("bounded_response",         len(text.strip())>=10 and not text.strip().startswith("I need more")),
        ],
        "english_comprehension": [("identifies_referent",_contains_any(lowered,["the model","it was","this is","they were","the candidate","the system","the result"])),("grammatically_aware",_contains_any(lowered,["promoted","corrected","revised","updated","fixed","was","were","has been"])),("paraphrases_correctly",_contains_any(lowered,["means","in other words","simplified","to say","equivalent to","that is","i.e."])),],
        "out_of_domain": [
            ("honest_about_limits",      _contains_any(lowered,["cannot","don't know","uncertain","unable","not sure","i lack","unknown","not able","cannot confirm"])),
            ("attempts_or_provides_answer",_contains_any(lowered,["answer is","result is","capital","ottawa","python","60","five","5 cups","http","transfer protocol","refuse","unknowable","three","red"])),
            ("does_not_hallucinate",     _is_substantial(text) and not _contains_any(lowered,["the winning numbers are","today's weather is exactly","i know for certain that"])),
        ],
    }
    checks = common + caps.get(capability, [])
    raw_score, matched = _score_parts(lowered, checks)
    normalized = round(raw_score / max(1, len(checks)), 4)
    if reference:
        notes.append(f"Scored against capability={capability} with {len(reference)} rubric fields.")
    notes.append(f"Matched {raw_score} of {len(checks)} checks.")
    return {"raw_score": raw_score, "normalized_score": normalized,
            "capability": capability, "notes": " ".join(notes), "matched_checks": matched}

def score_text(text: str) -> dict[str, Any]:
    return score_record(text, task=None)
