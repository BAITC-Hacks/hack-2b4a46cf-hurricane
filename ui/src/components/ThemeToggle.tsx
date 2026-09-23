import { useLingui } from "@lingui/react/macro";
import { Moon, Sun } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { getTheme, setTheme, type Theme } from "@/theme";

export function ThemeToggle() {
  const { t } = useLingui();
  const [theme, setCurrentTheme] = useState<Theme>(getTheme);
  const isDark = theme === "dark";

  function handleClick() {
    const next: Theme = isDark ? "light" : "dark";
    setTheme(next);
    setCurrentTheme(next);
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      onClick={handleClick}
      aria-pressed={isDark}
      aria-label={isDark ? t`Светлая тема` : t`Тёмная тема`}
      className="size-10 max-md:size-11"
    >
      {isDark ? (
        <Sun className="size-4" aria-hidden="true" />
      ) : (
        <Moon className="size-4" aria-hidden="true" />
      )}
    </Button>
  );
}
