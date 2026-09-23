/** Light/dark theme: the `dark` class on <html>, remembered in localStorage, system preference by default. */

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";
const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

export function getTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function getStoredTheme(): Theme | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "dark" || stored === "light" ? stored : null;
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function setTheme(theme: Theme) {
  applyTheme(theme);
  localStorage.setItem(STORAGE_KEY, theme);
}

export function applyStoredTheme() {
  applyTheme(getStoredTheme() ?? (systemTheme.matches ? "dark" : "light"));
  // Without an explicit choice the page follows the OS when it switches theme.
  systemTheme.addEventListener("change", (event) => {
    if (!getStoredTheme()) applyTheme(event.matches ? "dark" : "light");
  });
}
