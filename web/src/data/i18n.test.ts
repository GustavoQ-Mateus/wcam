import { describe, expect, it } from "vitest";
import en from "../../../locales/en.json" with { type: "json" };
import ptBR from "../../../locales/pt-BR.json" with { type: "json" };
import { errorMessageKey, resolveLanguage, translate } from "./i18n";

describe("i18n", () => {
  it("locales have the same keys in every language", () => {
    const englishKeys = Object.keys(en).sort();
    for (const locale of [ptBR]) {
      expect(Object.keys(locale).sort()).toEqual(englishKeys);
    }
  });

  it("language detection maps pt variants to pt-BR and others to en", () => {
    expect(["pt", "pt-BR", "pt-PT", "PT-br"].map(resolveLanguage)).toEqual(["pt-BR", "pt-BR", "pt-BR", "pt-BR"]);
    expect(["en", "en-US", "es-ES", "fr", ""].map(resolveLanguage)).toEqual(["en", "en", "en", "en", "en"]);
  });

  it("translation fills placeholders by name", () => {
    expect(translate("en", "console.pairing_expires", { seconds: "42" })).toBe(
      en["console.pairing_expires"].replace("{seconds}", "42"),
    );
  });

  it("unknown error code falls back to errors.unknown", () => {
    expect(errorMessageKey("not_same_network")).toBe("errors.not_same_network");
    expect(errorMessageKey("something_new")).toBe("errors.unknown");
  });
});
