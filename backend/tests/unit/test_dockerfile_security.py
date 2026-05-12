from pathlib import Path


def test_backend_dockerfile_uses_explicit_copy_paths() -> None:
    dockerfile = Path(__file__).resolve().parents[2] / "Dockerfile"
    copy_lines = [
        line.strip()
        for line in dockerfile.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("COPY ")
    ]

    assert "COPY . ." not in copy_lines
