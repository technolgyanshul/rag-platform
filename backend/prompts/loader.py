from __future__ import annotations

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent


def render_prompt(template_name: str, variables: dict[str, object]) -> str:
    template_path = PROMPTS_DIR / f"{template_name}.txt"
    template_text = template_path.read_text(encoding="utf-8")
    return template_text.format(**variables)
