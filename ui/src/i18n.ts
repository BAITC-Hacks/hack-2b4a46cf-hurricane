import { i18n } from "@lingui/core";

export const locales = ["ru", "kk", "en"] as const;
export type Locale = (typeof locales)[number];

export async function activateLocale(locale: Locale): Promise<void> {
  const { messages } = await import(`./locales/${locale}/messages.po`);
  i18n.load(locale, messages);
  i18n.activate(locale);
}

/** "2026-10-08" -> "8 октября 2026": full month name, since short names fall back to "M10" in some browsers. */
export function formatEventDate(isoDate: string, locale: string): string {
  const parts = new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).formatToParts(new Date(isoDate));
  const getPart = (type: string) =>
    parts.find((part) => part.type === type)?.value.replace(".", "") ?? "";
  return `${getPart("day")} ${getPart("month")} ${getPart("year")}`;
}

export function getInitialLocale(): Locale {
  const browserLocale = navigator.language.slice(0, 2);
  return locales.includes(browserLocale as Locale) ? (browserLocale as Locale) : "ru";
}
