# Evaluation Results

Stub benchmark comparing baseline and multi-agent flows.

## Summary

| System | Citation Hit Rate | Avg Completeness | Hallucination Rate | Avg Latency (ms) | Avg Judge Score |
|---|---:|---:|---:|---:|---:|
| multi-agent | 3/3 | 0.85 | 0.0 | 780 | 8.4 |
| single-agent | 3/3 | 0.7 | 0.0 | 520 | 7.2 |

## Per Question

| System | Question ID | Citation Hit | Expected Source | Completeness | Hallucination | Latency (ms) | Judge Score |
|---|---|---:|---|---:|---:|---:|---:|
| single-agent | q1 | yes | sample_1.pdf | 0.7 | no | 520 | 7.2 |
| single-agent | q2 | yes | sample_2.pdf | 0.7 | no | 520 | 7.2 |
| single-agent | q3 | yes | sample_image.png | 0.7 | no | 520 | 7.2 |
| multi-agent | q1 | yes | sample_1.pdf | 0.85 | no | 780 | 8.4 |
| multi-agent | q2 | yes | sample_2.pdf | 0.85 | no | 780 | 8.4 |
| multi-agent | q3 | yes | sample_image.png | 0.85 | no | 780 | 8.4 |

## Notes

Answers are currently stubs. Replace the evaluator with live `/query` API calls for real measurements.
