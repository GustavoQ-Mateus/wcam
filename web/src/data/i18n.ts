import en from "../../../locales/en.json" with { type: "json" };
import ptBR from "../../../locales/pt-BR.json" with { type: "json" };

export type Language = "en" | "pt-BR";
export type MessageKey = keyof typeof en;
export type MessageValues = Readonly<Record<string, string>>;

const MESSAGES: Record<Language, Record<MessageKey, string>> = { en, "pt-BR": ptBR };
const PORTUGUESE_PREFIX = "pt";
const PLACEHOLDER_PATTERN = /\{(\w+)\}/g;
const UNKNOWN_ERROR_KEY: MessageKey = "errors.unknown";

export function resolveLanguage(browserLanguage: string): Language {
  return browserLanguage.toLowerCase().startsWith(PORTUGUESE_PREFIX) ? "pt-BR" : "en";
}

export function translate(language: Language, key: MessageKey, values: MessageValues = {}): string {
  return MESSAGES[language][key].replace(
    PLACEHOLDER_PATTERN,
    (placeholder, name: string) => values[name] ?? placeholder,
  );
}

export function errorMessageKey(code: string): MessageKey {
  const key = `errors.${code}`;
  return isMessageKey(key) ? key : UNKNOWN_ERROR_KEY;
}

function isMessageKey(key: string): key is MessageKey {
  return Object.hasOwn(en, key);
}
