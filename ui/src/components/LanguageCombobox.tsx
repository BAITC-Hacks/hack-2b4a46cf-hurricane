import { Combobox as ComboboxPrimitive } from "@base-ui/react";
import { Trans } from "@lingui/react/macro";
import { Check } from "lucide-react";
import { Fragment } from "react";

import type { Schemas } from "@/api";
import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from "@/components/ui/combobox";

type Option = Schemas["OptionOut"];
type Language = Schemas["Language"];

export function LanguageCombobox({
  label,
  placeholder,
  options,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  options: Option[];
  value: Language[];
  onChange: (value: Language[]) => void;
}) {
  const anchor = useComboboxAnchor();
  const selected = options.filter((option) => value.includes(option.value as Language));

  return (
    <label className="grid min-w-0 content-start gap-2 text-sm font-medium">
      {label}
      <Combobox
        multiple
        items={options}
        value={selected}
        onValueChange={(next: Option[]) => onChange(next.map((option) => option.value as Language))}
        itemToStringLabel={(option: Option) => option.label}
        itemToStringValue={(option: Option) => option.value}
      >
        <ComboboxChips ref={anchor} className="min-h-10 w-full bg-background max-md:min-h-11">
          <ComboboxValue>
            {(chosen: Option[]) => (
              <Fragment>
                {chosen.map((option) => (
                  <ComboboxChip key={option.value}>{option.label}</ComboboxChip>
                ))}
                <ComboboxChipsInput placeholder={chosen.length ? "" : placeholder} />
              </Fragment>
            )}
          </ComboboxValue>
        </ComboboxChips>
        <ComboboxContent anchor={anchor}>
          <ComboboxEmpty>
            <Trans>Ничего не найдено</Trans>
          </ComboboxEmpty>
          <ComboboxList>
            {(option: Option) => (
              <ComboboxPrimitive.Item
                key={option.value}
                value={option}
                className="group flex min-h-11 cursor-default items-center gap-2 rounded-md px-3 text-sm outline-hidden select-none data-highlighted:bg-accent"
              >
                <span
                  aria-hidden="true"
                  className="flex size-4 shrink-0 items-center justify-center rounded-sm border border-input group-data-[selected]:border-primary group-data-[selected]:bg-primary group-data-[selected]:text-primary-foreground"
                >
                  <Check className="invisible size-3 group-data-[selected]:visible" />
                </span>
                {option.label}
              </ComboboxPrimitive.Item>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </label>
  );
}
