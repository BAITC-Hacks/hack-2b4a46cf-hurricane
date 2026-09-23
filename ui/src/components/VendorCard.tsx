import { Trans, useLingui } from "@lingui/react/macro";

import type { Schemas } from "@/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Vendor = Schemas["VendorOut"] | Schemas["VendorCardOut"];

export function VendorCard({ vendor }: { vendor: Vendor }) {
  const { t } = useLingui();
  const isRecommendation = "explanation" in vendor;
  const description = isRecommendation ? vendor.explanation : vendor.description;
  const role = isRecommendation
    ? {
        best_match: t`Лучшее совпадение`,
        best_price: t`Лучшая цена`,
        premium: t`Премиум`,
        alternative: t`Альтернатива`,
      }[vendor.role]
    : null;

  return (
    <Card className="h-full rounded-lg border border-border py-5 ring-0 [--card-spacing:--spacing(5)]">
      <CardHeader className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {role && (
            <span className="rounded-full border border-border bg-muted px-2 py-0.5">{role}</span>
          )}
          {vendor.synthetic && (
            <span className="rounded-full border border-border bg-muted px-2 py-0.5">
              <Trans>Синтетический профиль</Trans>
            </span>
          )}
        </div>
        <CardTitle className="text-base font-semibold">{vendor.name}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {vendor.city.label} · {vendor.categories.map((category) => category.label).join(", ")}
        </p>
      </CardHeader>
      <CardContent className="grid gap-3">
        <p className="text-sm font-medium">
          <Trans>От {new Intl.NumberFormat("ru-RU").format(vendor.price_from_kzt)} ₸</Trans>
        </p>
        <p className="line-clamp-3 text-sm leading-5 text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
