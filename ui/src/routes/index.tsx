import { Trans } from "@lingui/react/macro";
import { createFileRoute } from "@tanstack/react-router";
import { SearchX } from "lucide-react";
import { useState } from "react";

import { SearchForm, type SearchFilters } from "@/components/SearchForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/")({ component: HomePage });

// STUB: the recommendation form lands here once `POST /recommend` exists.
function HomePage() {
  const [selectedFilters, setSelectedFilters] = useState<SearchFilters | null>(null);

  return (
    <div className="grid gap-8 pb-12">
      <section className="grid gap-2">
        <h1 className="font-heading text-2xl font-semibold leading-8 max-md:text-xl max-md:leading-7">
          <Trans>Подрядчики под ваше событие</Trans>
        </h1>
        <p className="text-sm leading-5 text-muted-foreground">
          <Trans>Укажите главное — город, дату, формат и бюджет. Остальное можно уточнить.</Trans>
        </p>
      </section>
      <SearchForm onSearch={setSelectedFilters} onReset={() => setSelectedFilters(null)} />
      <Card
        className="rounded-lg border border-border py-6 shadow-card ring-0 [--card-spacing:--spacing(6)] max-md:py-4 max-md:[--card-spacing:--spacing(4)]"
        aria-live="polite"
      >
        <CardHeader>
          <CardTitle className="text-xl font-semibold">
            {selectedFilters ? <Trans>Фильтры выбраны</Trans> : <Trans>Результаты поиска</Trans>}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {selectedFilters ? (
            <>
              <div className="flex flex-wrap gap-2">
                {[
                  selectedFilters.city,
                  selectedFilters.event_format,
                  selectedFilters.category,
                  selectedFilters.language,
                  selectedFilters.duration_hours ? `${selectedFilters.duration_hours} ч` : null,
                ]
                  .filter(Boolean)
                  .map((value) => (
                    <span
                      key={value}
                      className="rounded-full border border-border bg-muted px-2 py-0.5 text-xs font-medium text-foreground"
                    >
                      {value}
                    </span>
                  ))}
              </div>
              <p className="text-base text-muted-foreground">
                <Trans>
                  Дата: {selectedFilters.event_date.split("-").reverse().join(".")} · Бюджет:{" "}
                  {new Intl.NumberFormat("ru-RU").format(selectedFilters.budget_kzt)} ₸
                </Trans>
              </p>
              <p className="text-base leading-6 text-muted-foreground">
                <Trans>Карточки подрядчиков появятся после подключения поиска к каталогу.</Trans>
              </p>
            </>
          ) : (
            <div className="grid justify-items-center gap-3 py-6 text-center">
              <SearchX className="size-10 text-muted-foreground" aria-hidden="true" />
              <h3 className="text-base font-semibold">
                <Trans>Пока нет результатов</Trans>
              </h3>
              <p className="text-xs text-muted-foreground">
                <Trans>После подключения поиска здесь появятся карточки подрядчиков.</Trans>
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
