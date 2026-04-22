# v2.2 resilience and comment refresh

This release adds a dedicated resilience subsystem for fallback selection, retry budgeting, and degraded completion tracking.

Highlights:
- failure classification for model and code-edit paths
- fallback history recorded as evaluation events
- `completed_fallback` and `partial_fallback` statuses for degraded completion
- symbol lookup now supports unique suffix fallback for methods/functions
- refreshed module-level docstrings and comments in modified runtime/code-edit files
