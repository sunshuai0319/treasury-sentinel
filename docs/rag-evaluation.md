# RAG Evaluation

This report records the live Milvus retrieval gate. It embeds each golden-set query with the configured local BGE model and searches the configured Milvus collection.

Queries: 20

| Metric | Actual | Threshold |
| --- | ---: | ---: |
| `recall_at_5` | 1.00 | 0.90 |
| `citation_accuracy` | 1.00 | 0.90 |
| `version_filter_accuracy` | 1.00 | 1.00 |
| `fail_closed_rate` | 1.00 | 1.00 |

Passed: `True`
