# Dataset Strategy

## Core split
- Train into weights: broad language, code, engineering reasoning, critique, repair, compression, calibration.
- Retrieve live: current repositories, repo state capsules, fast-changing source truth, specialized domain packs.
- Eval-only: verified challenge sets, paraphrase stability, quantization retention, adversarial checks.

## Local starter corpus rules
Every record should be:
- JSONL
- capability-labeled
- domain-labeled
- difficulty-labeled
- usable for benchmark slicing later

## Expansion targets
Starter phase target:
- 20+ records per dataset family
- 10+ tasks per benchmark family

Next phase target:
- 50+ records per dataset family
- 20+ tasks per benchmark family
