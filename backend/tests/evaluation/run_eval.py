from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    question_id: str
    question: str
    expected_source: str
    answer: str
    citation_hit: bool


def load_questions(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_stub(questions: list[dict[str, str]]) -> list[EvalResult]:
    results: list[EvalResult] = []
    for row in questions:
        expected_source = row["expected_source"]
        simulated_answer = f"Stub answer grounded in [{expected_source}#0]."
        results.append(
            EvalResult(
                question_id=row["id"],
                question=row["question"],
                expected_source=expected_source,
                answer=simulated_answer,
                citation_hit=expected_source in simulated_answer,
            )
        )
    return results


def write_markdown(results: list[EvalResult], output: Path) -> None:
    lines = [
        "# Evaluation Results",
        "",
        "| Question ID | Citation Hit | Expected Source | Answer |",
        "|---|---:|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result.question_id} | {'yes' if result.citation_hit else 'no'} | "
            f"{result.expected_source} | {result.answer} |"
        )
    lines.extend(
        [
            "",
            f"Citation hit rate: {sum(1 for row in results if row.citation_hit)}/{len(results)}",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    questions = load_questions(base_dir / "questions.json")
    report = evaluate_stub(questions)
    write_markdown(report, base_dir / "results.md")
    print(f"Wrote evaluation report for {len(report)} questions.")
