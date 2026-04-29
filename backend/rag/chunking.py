def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    normalized = (text or "").strip()
    if not normalized:
        return []

    if chunk_size <= 0:
        return [normalized]

    if chunk_overlap >= chunk_size:
        chunk_overlap = 0

    chunks: list[str] = []
    start = 0
    length = len(normalized)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = max(end - chunk_overlap, 0)

    return chunks
