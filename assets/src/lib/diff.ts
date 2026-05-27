import type { TranscriptionResult } from "../api/types";

function tokenize(text: string): string[] {
  return text.trim().split(/\s+/).filter(Boolean);
}

export type DiffToken = {
  text: string;
  changed: boolean;
};

export function diffAgainstBaseline(
  baseline: string,
  text: string,
): DiffToken[] {
  const baseTokens = new Set(tokenize(baseline));
  return tokenize(text).map((token) => ({
    text: token,
    changed: !baseTokens.has(token),
  }));
}

export function findFastestResult(
  results: TranscriptionResult[],
): TranscriptionResult | null {
  const ok = results.filter((r) => r.status === "ok");
  if (ok.length === 0) {
    return null;
  }
  return ok.reduce((best, current) =>
    current.latency_ms < best.latency_ms ? current : best,
  );
}

export function findCheapestResult(
  results: TranscriptionResult[],
): TranscriptionResult | null {
  const ok = results.filter((r) => r.status === "ok");
  if (ok.length === 0) {
    return null;
  }
  return ok.reduce((best, current) => {
    const bestCost = best.cost?.usd ?? best.estimated_cost_usd ?? Infinity;
    const currentCost =
      current.cost?.usd ?? current.estimated_cost_usd ?? Infinity;
    return currentCost < bestCost ? current : best;
  });
}

export function errorHint(error: string | null): string | null {
  if (!error) {
    return null;
  }
  const lower = error.toLowerCase();
  if (lower.includes("api key") || lower.includes("credential")) {
    return "Check API keys and credentials in your .env file.";
  }
  if (lower.includes("timeout")) {
    return "The provider timed out. Try a shorter clip or increase the timeout.";
  }
  return null;
}
