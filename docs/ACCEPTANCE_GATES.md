# Acceptance Gates

## Alpha gate
- Repo validates cleanly
- Dataset and benchmark counters run
- At least one adapter can complete the full benchmark loop
- Promotion report is generated
- Quantization-retention report is generated

## Beta gate
- Real local model backend runs through the benchmark loop
- Candidate vs incumbent comparison is enforced
- Minimal-prompt and bare-prompt results are recorded
- At least one retention comparison includes a real quantized candidate

## Frontier-aspirational gate
- Strong real local base model integrated
- Larger dataset families and benchmark families
- Repeatable improvement over incumbent on reasoning and repair
- No unacceptable regression in calibration or paraphrase stability
- GGUF variants tested locally with recorded retention metrics
