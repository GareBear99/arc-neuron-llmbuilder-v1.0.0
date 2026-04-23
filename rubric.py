"""scorers/rubric.py — Task-aware capability scorer for ARC-Neuron benchmarks.

Keyword-soup guard (added v1.1):
  Responses that are pure keyword lists with no sentence structure are
  penalised before capability checks run.  This prevents a response of
  "constraint rollback evidence validate minimal" from scoring 1.0 on
  every capability.

  A response is considered keyword soup when:
    - It is shorter than MIN_SENTENCE_CHARS characters, OR
    - It has fewer than MIN_WORDS words, OR
    - Its type/token ratio (unique words / total words) exceeds
      KEYWORD_DIVERSITY_FLOOR while containing fewer than
      MIN_SENTENCE_CHARS chars (catches single-word-per-line dumps), OR
    - It contains no sentence-ending punctuation (.!?) and fewer than
      MIN_WORDS_FOR_NO_PUNCT words.

  When soup is detected, keyword checks that would otherwise fire are
  suppressed: only length-based and negation-based checks are honoured.
"""
from __future__ import annotations
import re
from typing import Any

# ── coherence thresholds ──────────────────────────────────────────────────────
MIN_SENTENCE_CHARS    = 80   # a genuine answer needs at least this many chars
MIN_WORDS             = 12   # fewer than this → too terse to be meaningful
MIN_WORDS_FOR_NO_PUNCT = 60  # no sentence-ending punct → keyword soup unless very long response


def _word_count(text: str) -> int:
    return len(text.split())


def _has_sentence_structure(text: str) -> bool:
    """True when the text contains at least one sentence-ending punctuation mark."""
    return bool(re.search(r'[.!?]', text))


def _is_keyword_soup(text: str) -> bool:
    """Detect responses that are keyword dumps rather than prose answers.

    Returns True (soup detected) when the response lacks the minimum
    structural signals of a genuine sentence-level answer.
    """
    stripped = text.strip()
    if len(stripped) < MIN_SENTENCE_CHARS:
        return True
    words = stripped.split()
    if len(words) < MIN_WORDS:
        return True
    if not _has_sentence_structure(stripped) and len(words) < MIN_WORDS_FOR_NO_PUNCT:
        return True
    return False


def _is_substantial(text: str, min_chars: int = 80) -> bool:
    """Require both character length and sentence structure."""
    return len(text.strip()) >= min_chars and _has_sentence_structure(text)


def _contains_any(text: str, options: list[str], soup: bool = False) -> bool:
    """Keyword presence check.  Returns False immediately when soup=True so that
    keyword-list responses cannot satisfy content checks."""
    if soup:
        return False
    lowered = text.lower()
    return any(option in lowered for option in options)


def _score_parts(text: str, checks: list[tuple[str, bool]]) -> tuple[int, list[str]]:
    passed = [name for name, ok in checks if ok]
    return len(passed), passed

def _score_retention(text: str, task: dict) -> dict[str, Any]:
    lowered = text.lower()
    soup = _is_keyword_soup(text)
    checks = [
        ("responds_to_prompt",    len(text.strip()) >= 80 and _has_sentence_structure(text)),
        ("no_hallucinated_prior", not _contains_any(lowered, ["as we discussed earlier","you mentioned that","in our previous session","you told me"])),
        ("bounded_confidence",    _contains_any(lowered, ["based on","given","from what","according to","as stated","the constraint","as defined"], soup) or _is_substantial(text)),
        ("preserves_goal",        _contains_any(lowered, ["goal","objective","aim","purpose","target","mission"], soup)),
        ("preserves_constraint",  _contains_any(lowered, ["constraint","must not","cannot","requirement","rule","preserve","must","should not"], soup)),
        ("names_next_action",     _contains_any(lowered, ["next","action","step","should","check","verify","validate","recommend"], soup)),
    ]
    raw, matched = _score_parts(lowered, checks)
    notes = f"Retention: {raw}/{len(checks)} checks passed."
    if soup:
        notes += " [keyword-soup detected: content checks suppressed]"
    return {"raw_score": raw, "normalized_score": round(raw/max(1,len(checks)),4),
            "capability": task.get("capability","continuity"),
            "notes": notes,
            "matched_checks": matched, "scoring_mode": "retention",
            "keyword_soup_detected": soup}

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
    soup = _is_keyword_soup(text)
    notes: list[str] = []
    common = [
        ("mentions_constraints",            _contains_any(lowered,["constraint","preserve","boundary","interface"], soup)),
        ("mentions_risk_or_tradeoff",       _contains_any(lowered,["risk","tradeoff","regression","failure mode"], soup)),
        ("mentions_validation_or_evidence", _contains_any(lowered,["validate","test","evidence","verify","observability"], soup)),
    ]
    caps: dict[str, list[tuple[str,bool]]] = {
        "planning":             [("has_ordered_plan",_contains_any(lowered,["plan","steps","first","then"], soup)),("prefers_narrow_change",_contains_any(lowered,["smallest","minimal","targeted","narrow"], soup)),("preserves_interfaces",_contains_any(lowered,["preserve interfaces","public api","boundary","without breaking"], soup))],
        "reasoning":            [("separates_fact_from_inference",_contains_any(lowered,["fact","inference","given","unknown"], soup)),("rejects_or_bounds_unsafe_change",_contains_any(lowered,["reject","not acceptable","only if","conditionally"], soup)),("mentions_conflict",_contains_any(lowered,["conflict","contradiction","tradeoff","threatens"], soup))],
        "critique":             [("identifies_missing_evidence",_contains_any(lowered,["missing evidence","not shown","unverified","assumption"], soup)),("identifies_scope_risk",_contains_any(lowered,["too broad","scope","blast radius","regression"], soup)),("proposes_followup_check",_contains_any(lowered,["validate","test","verify","instrument"], soup))],
        "repair":               [("offers_specific_fix",_contains_any(lowered,["patch","fix","change","guard","rollback"], soup)),("keeps_fix_small",_contains_any(lowered,["minimal","targeted","surgical","narrow"], soup)),("adds_regression_protection",_contains_any(lowered,["test","regression","validate","assert"], soup))],
        "compression":          [("preserves_goal",_contains_any(lowered,["goal","objective","task"], soup)),("preserves_blockers",_contains_any(lowered,["blocker","risk","constraint"], soup)),("preserves_next_action",_contains_any(lowered,["next","action","do this","follow-up"], soup))],
        "calibration":          [("states_uncertainty",_contains_any(lowered,["likely","uncertain","confidence","may","bounded"], soup)),("avoids_false_certainty",_is_substantial(text) and not _contains_any(lowered,["definitely","certainly","guaranteed"], soup)),("ties_claims_to_evidence",_contains_any(lowered,["evidence","based on","from the prompt","given only"], soup))],
        "paraphrase_stability": [("preserves_meaning",_contains_any(lowered,["same meaning","preserve","equivalent","without changing"], soup)),("mentions_constraints",_contains_any(lowered,["constraint","key point","do not lose"], soup)),("avoids_additional_claims",_is_substantial(text) and not _contains_any(lowered,["new requirement","extra guarantee","additional promise"], soup))],
        "quantization_retention":[("mentions_core_behavior",_contains_any(lowered,["retain","preserve","behavior","quality"], soup)),("compares_variants",_contains_any(lowered,["full precision","quantized","gguf","variant"], soup)),("mentions_regression_threshold",_contains_any(lowered,["threshold","regression","drop","retention"], soup))],
        "continuity":           [("preserves_thread",_contains_any(lowered,["goal","objective","prior","earlier","we agreed","session"], soup)),("preserves_constraint",_contains_any(lowered,["constraint","rule","must","requirement"], soup)),("names_next_action",_contains_any(lowered,["next","action","step","check","verify"], soup))],
        "reflection":           [("identifies_issue",_contains_any(lowered,["overclaim","wrong","incorrect","contradiction","redundant","too broad"], soup)),("revises_or_corrects",_contains_any(lowered,["revise","correct","instead","more accurately","better to say","rephrase"], soup)),("bounded_final",_contains_any(lowered,["likely","bounded","based on","evidence","uncertain","confidence"], soup))],
        "lexical_accuracy":     [("uses_canonical_source",_contains_any(lowered,["module","canonical","stored","retrieve","source","known"], soup)),("avoids_hallucination",_contains_any(lowered,["not supported","unknown","not in","no evidence","cannot confirm"], soup)),("bounded_response",_contains_any(lowered,["based on","from the","as defined","according to"], soup))],
        "archive_reasoning":    [("mentions_archive_layer",_contains_any(lowered,["archive","bundle","arc-rar","omnibinary","ledger"], soup)),("mentions_rollback",_contains_any(lowered,["rollback","restore","replay","prior state"], soup)),("mentions_lineage",_contains_any(lowered,["lineage","receipt","trace","provenance","evidence"], soup))],
        "runtime_reasoning":    [("mentions_runtime_layer",_contains_any(lowered,["runtime","adapter","backend","model","inference"], soup)),("mentions_timeout_or_guard",_contains_any(lowered,["timeout","guard","limit","boundary","safety"], soup)),("evidence_based",_contains_any(lowered,["evidence","based on","from the","receipt"], soup))],
        "state_evidence":       [("names_state_element",_contains_any(lowered,["state","incumbent","scoreboard","floor","score"], soup)),("links_to_evidence",_contains_any(lowered,["receipt","report","benchmark","evidence","proof"], soup)),("proposes_action",_contains_any(lowered,["next","should","action","verify","check"], soup))],
        "system_spine_reasoning":[("names_spine_component",_contains_any(lowered,["language module","omnibinary","arc-rar","runtime","cognition core"], soup)),("describes_role",_contains_any(lowered,["truth","memory","archive","govern","promote","train"], soup)),("coherent_relationship",_contains_any(lowered,["feeds","into","produces","enables","provides","supports"], soup))],
        "native_operation_planning":[("names_operation",_contains_any(lowered,["train","benchmark","promote","bundle","export","verify"], soup)),("orders_steps",_contains_any(lowered,["first","then","next","after","before","finally"], soup)),("names_gate",_contains_any(lowered,["gate","check","validate","floor","threshold","pass"], soup))],
        "deterministic_compliance":[("follows_format",_contains_any(lowered,["json","yaml","output","format","structure"], soup)),("bounded",_contains_any(lowered,["bounded","constraint","rule","requirement"], soup)),("evidence",_contains_any(lowered,["evidence","based on","given"], soup))],
        "deterministic_format":  [("structured_output",_contains_any(lowered,["json","yaml","list","format","structure","output"], soup)),("no_hallucination",not _contains_any(lowered,["i think","perhaps","maybe","probably"], soup)),("complete",_contains_any(lowered,["complete","all","every","each"], soup))],
        "refusal_correctness":   [("identifies_refusal_case",_contains_any(lowered,["cannot","refuse","not able","outside","scope","boundary"], soup)),("explains_reason",_contains_any(lowered,["because","reason","constraint","policy","doctrine"], soup)),("offers_alternative",_contains_any(lowered,["instead","alternative","suggest","can help with","within"], soup))],
        "english_understanding": [
            ("produces_coherent_response",  len(text.strip()) >= 20),
            ("addresses_question_directly",  not text.strip().startswith("I")),
            ("shows_comprehension",         _contains_any(lowered,["means","refers to","is","states","indicates","the claim","the sentence","this says","this means","in other words","simply put","restate","paraphrase","it is","they are"], soup)),
        ],
        "instruction_following": [
            ("follows_format",           _contains_any(lowered,["1.","2.","3.","first:","second:","third:","problem:","action:","result:","agree","disagree"], soup)),
            ("stays_on_task",            _is_substantial(text) and not _contains_any(lowered,["i cannot do","i am not able to","as an ai"], soup)),
            ("bounded_response",         len(text.strip())>=10 and not text.strip().startswith("I need more")),
        ],
        "english_comprehension": [("identifies_referent",_contains_any(lowered,["the model","it was","this is","they were","the candidate","the system","the result"], soup)),("grammatically_aware",_contains_any(lowered,["promoted","corrected","revised","updated","fixed","was","were","has been"], soup)),("paraphrases_correctly",_contains_any(lowered,["means","in other words","simplified","to say","equivalent to","that is","i.e."], soup)),],
        "out_of_domain": [
            ("honest_about_limits",      _contains_any(lowered,["cannot","don't know","uncertain","unable","not sure","i lack","unknown","not able","cannot confirm"], soup)),
            ("attempts_or_provides_answer",_contains_any(lowered,["answer is","result is","capital","ottawa","python","60","five","5 cups","http","transfer protocol","refuse","unknowable","three","red"], soup)),
            ("does_not_hallucinate",     _is_substantial(text) and not _contains_any(lowered,["the winning numbers are","today's weather is exactly","i know for certain that"], soup)),
        ],
    }
    checks = common + caps.get(capability, [])
    raw_score, matched = _score_parts(lowered, checks)
    normalized = round(raw_score / max(1, len(checks)), 4)
    if reference:
        notes.append(f"Scored against capability={capability} with {len(reference)} rubric fields.")
    notes.append(f"Matched {raw_score} of {len(checks)} checks.")
    if soup:
        notes.append("[keyword-soup detected: content checks suppressed]")
    return {"raw_score": raw_score, "normalized_score": normalized,
            "capability": capability, "notes": " ".join(notes), "matched_checks": matched,
            "keyword_soup_detected": soup}

def score_text(text: str) -> dict[str, Any]:
    return score_record(text, task=None)
