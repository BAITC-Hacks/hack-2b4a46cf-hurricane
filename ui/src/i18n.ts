import { i18n } from "@lingui/core";

export const locales = ["ru", "kk", "en"] as const;
export type Locale = (typeof locales)[number];

export async function activateLocale(locale: Locale): Promise<void> {
  const { messages } = await import(`./locales/${locale}/messages.po`);
  i18n.load(locale, messages);
  i18n.activate(locale);
}

export function getInitialLocale(): Locale {
  const browserLocale = navigator.language.slice(0, 2);
  return locales.includes(browserLocale as Locale) ? (browserLocale as Locale) : "ru";
}
