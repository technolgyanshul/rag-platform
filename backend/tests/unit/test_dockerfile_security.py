from pathlib import Path


def test_backend_dockerfile_uses_explicit_copy_paths() -> None:
    dockerfile = Path(__file__).resolve().parents[2] / "Dockerfile"
    copy_lines = [
        line.strip()
        for line in dockerfile.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("COPY ")
    ]

    assert "COPY . ." not in copy_lines


def test_backend_dockerfile_copy_resources_are_not_writable() -> None:
    dockerfile = Path(__file__).resolve().parents[2] / "Dockerfile"
    copy_lines = [
        line.strip()
        for line in dockerfile.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("COPY ")
    ]

    assert copy_lines
    for line in copy_lines:
        assert "--chmod=" in line
        chmod_value = line.split("--chmod=", 1)[1].split(maxsplit=1)[0]
        assert not any(int(digit) & 0o2 for digit in chmod_value[-3:])
