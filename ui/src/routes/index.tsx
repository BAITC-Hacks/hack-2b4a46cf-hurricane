import { Trans } from "@lingui/react/macro";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { LoaderCircle, SearchX } from "lucide-react";
import { useState } from "react";

import { fetchCatalogOptions, fetchVendors } from "@/api";
import { SearchForm, type SearchFilters } from "@/components/SearchForm";
import { Button } from "@/components/ui/button";
import { VendorCard } from "@/components/VendorCard";

export const Route = createFileRoute("/")({ component: HomePage });

function HomePage() {
  const navigate = useNavigate();
  const [showAllVendors, setShowAllVendors] = useState(false);
  const options = useQuery({ queryKey: ["catalog", "options"], queryFn: fetchCatalogOptions });
  const vendors = useQuery({ queryKey: ["vendors"], queryFn: fetchVendors });

  function handleSearch(filters: SearchFilters) {
    navigate({
      to: "/results",
      search: {
        city: filters.city,
        event_date: filters.event_date,
        event_format: filters.event_format,
        category: filters.category,
        budget_kzt: filters.budget_kzt,
        ...(filters.duration_hours ? { duration_hours: filters.duration_hours } : {}),
        ...(filters.languages?.length ? { languages: filters.languages.join(",") } : {}),
      },
    });
  }

  return (
    <div className="grid gap-8 pb-12">
      <section className="grid gap-2">
        <h1 className="font-heading text-2xl font-semibold leading-8 max-md:text-xl max-md:leading-7">
          <Trans>Подрядчики под ваше событие</Trans>
        </h1>
        <p className="text-sm leading-5 text-muted-foreground">
          <Trans>Укажите город, дату, формат и бюджет, чтобы найти подходящих подрядчиков.</Trans>
        </p>
      </section>
      {options.isPending ? (
        <div className="flex min-h-40 items-center gap-2 rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
          <Trans>Загружаю фильтры…</Trans>
        </div>
      ) : options.isError ? (
        <div className="grid gap-3 rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-destructive">
            <Trans>Не удалось загрузить фильтры. Попробуйте ещё раз.</Trans>
          </p>
          <Button
            variant="outline"
            onClick={() => options.refetch()}
            className="w-fit max-md:w-full"
          >
            <Trans>Повторить</Trans>
          </Button>
        </div>
      ) : (
        <SearchForm options={options.data} onSearch={handleSearch} />
      )}
      <section className="grid gap-4" aria-live="polite">
        <h2 className="text-xl font-semibold">
          <Trans>Подрядчики</Trans>
        </h2>
        {vendors.isPending ? (
          <div className="flex min-h-32 items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
            <Trans>Загружаю подрядчиков…</Trans>
          </div>
        ) : vendors.isError ? (
          <div className="grid gap-3 rounded-lg border border-border bg-card p-6">
            <p className="text-sm text-destructive">
              <Trans>Не удалось загрузить подрядчиков. Попробуйте ещё раз.</Trans>
            </p>
            <Button
              variant="outline"
              onClick={() => vendors.refetch()}
              className="w-fit max-md:w-full"
            >
              <Trans>Повторить</Trans>
            </Button>
          </div>
        ) : vendors.data.length === 0 ? (
          <div className="grid justify-items-center gap-2 rounded-lg border border-border bg-card p-8 text-center">
            <SearchX className="size-10 text-muted-foreground" aria-hidden="true" />
            <p className="font-semibold">
              <Trans>Подрядчиков пока нет</Trans>
            </p>
            <p className="text-sm text-muted-foreground">
              <Trans>Попробуйте вернуться позже.</Trans>
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
              {(showAllVendors ? vendors.data : vendors.data.slice(0, 6)).map((vendor) => (
                <VendorCard key={vendor.id} vendor={vendor} />
              ))}
            </div>
            {!showAllVendors && vendors.data.length > 6 && (
              <Button
                variant="outline"
                onClick={() => setShowAllVendors(true)}
                className="w-fit max-md:w-full"
              >
                <Trans>Показать всех подрядчиков ({vendors.data.length})</Trans>
              </Button>
            )}
          </>
        )}
      </section>
    </div>
  );
}
