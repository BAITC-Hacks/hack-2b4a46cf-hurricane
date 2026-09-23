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
    <div className="mx-auto max-w-4xl px-6 py-6 max-md:px-3 max-md:py-2">
      <header className="mb-4 flex items-center justify-between gap-3 border-b border-border pb-3 max-md:mb-3 max-md:pb-2">
        <p className="text-lg font-semibold tracking-tight">
          <Link to="/">
            <Trans>EventMatch</Trans>
          </Link>
        </p>
        <div className="flex items-center gap-3">
          <Select value={i18n.locale} onValueChange={(value) => activateLocale(value as Locale)}>
            <SelectTrigger className="min-h-10 w-16 px-2 uppercase max-md:min-h-11">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="end" className="min-w-20">
              {locales.map((locale) => (
                <SelectItem key={locale} value={locale} className="min-h-11">
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
