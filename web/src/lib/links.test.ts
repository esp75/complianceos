import { describe, expect, test } from "bun:test";
import { contactHref, safeHref } from "./links";

describe("safeHref", () => {
  test("keeps http(s), mailto and tel", () => {
    expect(safeHref("https://example.org")).toBe("https://example.org");
    expect(safeHref("mailto:a@b.org")).toBe("mailto:a@b.org");
    expect(safeHref("tel:+352123")).toBe("tel:+352123");
  });
  test("drops script and data URLs", () => {
    expect(safeHref("javascript:alert(1)")).toBeUndefined();
    expect(safeHref("  JavaScript:alert(1)")).toBeUndefined();
    expect(safeHref("data:text/html,x")).toBeUndefined();
    expect(safeHref(null)).toBeUndefined();
  });
  test("contact links by kind", () => {
    expect(contactHref("email", "info@space-agency.lu")).toBe("mailto:info@space-agency.lu");
    expect(contactHref("phone", "+352 288 482 10")).toBe("tel:+35228848210");
    expect(contactHref("postal", "12C Impasse")).toBeUndefined();
    expect(contactHref("web_form", "javascript:alert(1)")).toBeUndefined();
  });
});
