import { defineConfig } from "@lingui/cli";

export default defineConfig({
  sourceLocale: "ru",
  locales: ["ru", "kk", "en"],
  catalogs: [{ path: "<rootDir>/src/locales/{locale}/messages", include: ["src"] }],
});
