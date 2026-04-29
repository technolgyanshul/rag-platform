from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    system: str
    question_id: str
    question: str
    expected_source: str
    answer: str
    citation_hit: bool
    completeness_score: float
    hallucination_flag: bool
    latency_ms: int
    judge_score: float


def load_questions(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_stub(questions: list[dict[str, str]], system: str) -> list[EvalResult]:
    results: list[EvalResult] = []
    for row in questions:
        expected_source = row["expected_source"]
        simulated_answer = f"{system} stub answer grounded in [{expected_source}#0]."
        citation_hit = expected_source in simulated_answer
        completeness_score = 0.7 if system == "single-agent" else 0.85
        hallucination_flag = False
        latency_ms = 520 if system == "single-agent" else 780
        judge_score = 7.2 if system == "single-agent" else 8.4
        results.append(
            EvalResult(
                system=system,
                question_id=row["id"],
                question=row["question"],
                expected_source=expected_source,
                answer=simulated_answer,
                citation_hit=citation_hit,
                completeness_score=completeness_score,
                hallucination_flag=hallucination_flag,
                latency_ms=latency_ms,
                judge_score=judge_score,
            )
        )
    return results


def write_markdown(results: list[EvalResult], output: Path) -> None:
    systems = sorted({row.system for row in results})
    summary_lines = ["## Summary", "", "| System | Citation Hit Rate | Avg Completeness | Hallucination Rate | Avg Latency (ms) | Avg Judge Score |", "|---|---:|---:|---:|---:|---:|"]
    for system in systems:
        scoped = [row for row in results if row.system == system]
        count = len(scoped)
        citation_hits = sum(1 for row in scoped if row.citation_hit)
        avg_completeness = round(sum(row.completeness_score for row in scoped) / count, 2)
        hallucination_rate = round(sum(1 for row in scoped if row.hallucination_flag) / count, 2)
        avg_latency = int(sum(row.latency_ms for row in scoped) / count)
        avg_judge = round(sum(row.judge_score for row in scoped) / count, 2)
        summary_lines.append(
            f"| {system} | {citation_hits}/{count} | {avg_completeness} | {hallucination_rate} | {avg_latency} | {avg_judge} |"
        )

    lines = [
        "# Evaluation Results",
        "",
        "Stub benchmark comparing baseline and multi-agent flows.",
        "",
        *summary_lines,
        "",
        "## Per Question",
        "",
        "| System | Question ID | Citation Hit | Expected Source | Completeness | Hallucination | Latency (ms) | Judge Score |",
        "|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| {result.system} | {result.question_id} | {'yes' if result.citation_hit else 'no'} | "
            f"{result.expected_source} | {result.completeness_score} | "
            f"{'yes' if result.hallucination_flag else 'no'} | {result.latency_ms} | {result.judge_score} |"
        )
    lines.extend(["", "## Notes", "", "Answers are currently stubs. Replace the evaluator with live `/query` API calls for real measurements."])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    questions = load_questions(base_dir / "questions.json")
    report = [
        *evaluate_stub(questions, system="single-agent"),
        *evaluate_stub(questions, system="multi-agent"),
    ]
    write_markdown(report, base_dir / "results.md")
    print(f"Wrote evaluation report for {len(report)} questions.")
