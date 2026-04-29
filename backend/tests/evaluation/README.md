# Evaluation Fixtures

This directory contains Phase 8 evaluation scaffolding.

## Files

- `questions.json`: lightweight evaluation set with expected source labels
- `run_eval.py`: script that generates a markdown report from questions
- `results.md`: generated output report

## Run

```bash
python backend/tests/evaluation/run_eval.py
```

The current script uses a stub evaluator. Replace `evaluate_stub()` with live API calls for full baseline vs multi-agent comparison.
