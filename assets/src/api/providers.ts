import type { LanguageOption, ProviderStatus } from "./types";

export async function fetchProviders(): Promise<ProviderStatus[]> {
  const response = await fetch("/api/providers");
  if (!response.ok) {
    throw new Error("Failed to load providers");
  }
  const payload = (await response.json()) as { providers: ProviderStatus[] };
  return payload.providers;
}

export async function fetchLanguages(): Promise<LanguageOption[]> {
  const response = await fetch("/api/languages");
  if (!response.ok) {
    throw new Error("Failed to load languages");
  }
  const payload = (await response.json()) as { languages: LanguageOption[] };
  return payload.languages;
}
