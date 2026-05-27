import { useEffect, useMemo, useState } from "react";
import type { TranscriptionResult } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { diffAgainstBaseline, findFastestResult } from "@/lib/diff";
import { formatLatency, providerInitials } from "@/lib/format";
import { cn } from "@/lib/utils";

type CompareViewProps = {
  results: TranscriptionResult[];
};

export function CompareView({ results }: CompareViewProps) {
  const okResults = useMemo(
    () => results.filter((result) => result.status === "ok"),
    [results],
  );
  const [baselineId, setBaselineId] = useState("");

  useEffect(() => {
    const fastestId = findFastestResult(results)?.provider_id;
    const fallbackId = okResults[0]?.provider_id ?? "";
    setBaselineId((current) => {
      if (current && okResults.some((result) => result.provider_id === current)) {
        return current;
      }
      return fastestId ?? fallbackId;
    });
  }, [okResults, results]);

  const baseline = okResults.find((result) => result.provider_id === baselineId);
  const baselineText = baseline?.text ?? "";

  if (okResults.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        No successful transcripts to compare yet.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        Choose a baseline on any card. Amber highlights show words that differ
        from it.
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        {okResults.map((result) => {
          const name = result.display_name ?? result.provider_id;
          const isBaseline = result.provider_id === baselineId;
          const tokens =
            baselineText && !isBaseline
              ? diffAgainstBaseline(baselineText, result.text ?? "")
              : (result.text ?? "")
                  .trim()
                  .split(/\s+/)
                  .filter(Boolean)
                  .map((text) => ({ text, changed: false }));

          return (
            <article
              key={result.provider_id}
              className={cn(
                "rounded-2xl border bg-zinc-900/70 p-5",
                isBaseline
                  ? "border-emerald-800/70 ring-1 ring-emerald-900/40"
                  : "border-zinc-800",
              )}
            >
              <header className="mb-3 flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-emerald-300">
                    {providerInitials(name)}
                  </span>
                  <div className="min-w-0">
                    <h3 className="truncate font-medium text-zinc-100">{name}</h3>
                    <span className="text-xs text-zinc-400">
                      {formatLatency(result.latency_ms)}
                    </span>
                  </div>
                </div>
                {isBaseline ? (
                  <Badge variant="success" className="shrink-0">
                    Baseline
                  </Badge>
                ) : (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="h-8 shrink-0 whitespace-nowrap px-2.5 text-xs"
                    onClick={() => setBaselineId(result.provider_id)}
                  >
                    Use as baseline
                  </Button>
                )}
              </header>
              <p className="text-sm leading-relaxed text-zinc-200">
                {tokens.map((token, index) => (
                  <span
                    key={`${result.provider_id}-${index}`}
                    className={
                      token.changed ? "rounded bg-amber-950/60 text-amber-200" : ""
                    }
                  >
                    {token.text}
                    {index < tokens.length - 1 ? " " : ""}
                  </span>
                ))}
              </p>
            </article>
          );
        })}
      </div>
    </div>
  );
}
