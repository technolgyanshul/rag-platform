# Evaluation

## Goal

Compare baseline answer quality against multi-agent pipeline quality using repeatable prompts and expected source attribution.

## Current Scaffold

- Question set: `backend/tests/evaluation/questions.json`
- Runner: `backend/tests/evaluation/run_eval.py`
- Report output: `backend/tests/evaluation/results.md`

## Next Step

Replace the stub evaluator with live `/query` calls and record:

- citation correctness
- answer completeness
- hallucination rate
- latency per query
- judge score trends
