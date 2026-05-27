import { useCallback, useEffect, useState } from "react";
import { fetchLanguages, fetchProviders } from "@/api/providers";
import type { LanguageOption, ProviderStatus } from "@/api/types";

export function useProviders() {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [languages, setLanguages] = useState<LanguageOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [providerData, languageData] = await Promise.all([
        fetchProviders(),
        fetchLanguages(),
      ]);
      setProviders(providerData);
      setLanguages(languageData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { providers, languages, loading, error, refresh };
}
