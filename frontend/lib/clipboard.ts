type SelectableField = {
  value: string;
  selectionStart: number | null;
  selectionEnd: number | null;
};

function isSelectableField(value: unknown): value is SelectableField {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.value === "string"
    && (typeof candidate.selectionStart === "number" || candidate.selectionStart === null)
    && (typeof candidate.selectionEnd === "number" || candidate.selectionEnd === null)
  );
}

/** Returns only currently selected text from active input/textarea-like fields. */
export function fieldOnlyClipboardText(activeElement: unknown): string | null {
  if (!isSelectableField(activeElement)) {
    return null;
  }
  const rawValue = activeElement.value;
  const start = activeElement.selectionStart;
  const end = activeElement.selectionEnd;
  if (typeof start !== "number" || typeof end !== "number") {
    return rawValue;
  }
  const from = Math.max(0, Math.min(start, end));
  const to = Math.min(rawValue.length, Math.max(start, end));
  return rawValue.slice(from, to);
}
