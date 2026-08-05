# RAG Evaluation

This report records the offline policy citation gate. It verifies that the golden-set
expected policy documents, versions, and sections are present before live Milvus
evaluation is trusted.

Queries: 20

| Metric | Actual | Threshold |
| --- | ---: | ---: |
| `recall_at_5` | 1.00 | 0.90 |
| `citation_accuracy` | 1.00 | 0.90 |
| `version_filter_accuracy` | 1.00 | 1.00 |
| `fail_closed_rate` | 1.00 | 1.00 |

Passed: `True`
