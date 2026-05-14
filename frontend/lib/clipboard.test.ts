import { describe, expect, it } from "vitest";

import { fieldOnlyClipboardText } from "./clipboard";

describe("fieldOnlyClipboardText", () => {
  it("returns selected substring for focused field-like object", () => {
    expect(
      fieldOnlyClipboardText({
        value: "alpha beta gamma",
        selectionStart: 6,
        selectionEnd: 10,
      }),
    ).toBe("beta");
  });

  it("returns entire value when selection bounds are unavailable", () => {
    expect(
      fieldOnlyClipboardText({
        value: "full text",
        selectionStart: null,
        selectionEnd: null,
      }),
    ).toBe("full text");
  });

  it("returns null for non-field active elements", () => {
    expect(fieldOnlyClipboardText({ textContent: "trace log output" })).toBeNull();
    expect(fieldOnlyClipboardText(null)).toBeNull();
  });
});
