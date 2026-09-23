import { Trans, useLingui } from "@lingui/react/macro";
import type { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Link, Outlet } from "@tanstack/react-router";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { activateLocale, locales, type Locale } from "@/i18n";

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootLayout,
});

function RootLayout() {
  const { i18n } = useLingui();

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 max-md:px-4 max-md:py-4">
      <header className="mb-8 flex items-center justify-between max-md:mb-5 max-md:flex-col max-md:items-stretch max-md:gap-3">
        <h1 className="text-2xl font-semibold max-md:text-xl">
          <Link to="/">
            <Trans>Приложение</Trans>
          </Link>
        </h1>
        <div className="flex items-center gap-3 max-md:flex-col max-md:items-stretch">
          <Select value={i18n.locale} onValueChange={(value) => activateLocale(value as Locale)}>
            <SelectTrigger className="w-24 max-md:w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {locales.map((locale) => (
                <SelectItem key={locale} value={locale}>
                  {locale.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
