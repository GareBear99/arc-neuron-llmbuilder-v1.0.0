# heuristic_minimal_doctrine

## Summary
- Adapter: heuristic
- Prompt profile: minimal_doctrine

## Intended role
Candidate cognition model evaluated inside the cognition lab package.

## Current metrics snapshot
```json
{
  "models": [
    {
      "model": "heuristic_minimal_doctrine",
      "reasoning_accuracy": 0.2857,
      "planning_quality": 0.3,
      "critique_usefulness": 0.4286,
      "repair_success": 0.4286,
      "compression_retention": 0.3286,
      "calibration_error": 0.7143,
      "paraphrase_stability": 0.7286,
      "overall_weighted_score": 0.4554
    },
    {
      "model": "heuristic_gate_v1",
      "reasoning_accuracy": 0.2857,
      "planning_quality": 0.3,
      "critique_usefulness": 0.4286,
      "repair_success": 0.4286,
      "compression_retention": 0.3286,
      "calibration_error": 0.7143,
      "paraphrase_stability": 0.7286,
      "overall_weighted_score": 0.4554
    },
    {
      "model": "heuristic_gate_v1",
      "reasoning_accuracy": 0.2857,
      "planning_quality": 0.3,
      "critique_usefulness": 0.4286,
      "repair_success": 0.4286,
      "compression_retention": 0.3286,
      "calibration_error": 0.7143,
      "paraphrase_stability": 0.7286,
      "overall_weighted_score": 0.4554
    }
  ]
}
```

## Known limitations
- Alpha lab scaffold
- Not a trained frontier checkpoint by default
- Benchmark scoring is starter-grade unless replaced with richer evaluators
