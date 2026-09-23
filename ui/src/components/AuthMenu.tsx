import { useLingui } from "@lingui/react/macro";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { fetchCurrentUser, loginWithTelegram, type TelegramAuthPayload } from "@/api";
import { clearSessionToken, getSessionToken, saveSessionToken } from "@/auth";
import { Button } from "@/components/ui/button";
import { TelegramLoginButton } from "@/components/TelegramLoginButton";

export const CURRENT_USER_KEY = ["auth", "me"];

export function AuthMenu() {
  const { t } = useLingui();
  const queryClient = useQueryClient();
  const currentUser = useQuery({
    queryKey: CURRENT_USER_KEY,
    queryFn: fetchCurrentUser,
    enabled: getSessionToken() !== null,
    retry: false,
  });
  const login = useMutation({
    mutationFn: loginWithTelegram,
    onSuccess: (session) => {
      saveSessionToken(session.token);
      queryClient.setQueryData(CURRENT_USER_KEY, session.user);
    },
  });

  const handleTelegramAuth = useCallback(
    (payload: TelegramAuthPayload) => login.mutate(payload),
    [login],
  );

  function handleLogout() {
    clearSessionToken();
    queryClient.removeQueries({ queryKey: CURRENT_USER_KEY });
  }

  if (currentUser.data) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">{currentUser.data.first_name}</span>
        <Button variant="outline" onClick={handleLogout}>
          {t`Выйти`}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1 max-md:items-stretch">
      <TelegramLoginButton onAuth={handleTelegramAuth} />
      {login.isError && <span className="text-xs text-destructive">{login.error.message}</span>}
    </div>
  );
}
