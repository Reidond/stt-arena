import { useMemo } from "react";
import type { BatchRun } from "@/api/types";
import { CompareView } from "@/components/results/CompareView";
import { ExportToolbar } from "@/components/results/ExportToolbar";
import { ResultCard } from "@/components/results/ResultCard";
import { ResultTable } from "@/components/results/ResultTable";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { findCheapestResult, findFastestResult } from "@/lib/diff";

type ResultsWorkspaceProps = {
  runs: BatchRun[];
};

function badgesForResult(
  resultId: string,
  results: BatchRun["results"],
): string[] {
  const badges: string[] = [];
  const fastest = findFastestResult(results);
  const cheapest = findCheapestResult(results);
  if (fastest?.provider_id === resultId) {
    badges.push("Fastest");
  }
  if (cheapest?.provider_id === resultId && cheapest.provider_id !== fastest?.provider_id) {
    badges.push("Lowest cost");
  } else if (cheapest?.provider_id === resultId && fastest?.provider_id === resultId) {
    badges.push("Lowest cost");
  }
  return badges;
}

function RunResults({ run }: { run: BatchRun }) {
  const resultMap = useMemo(
    () => Object.fromEntries(run.results.map((result) => [result.provider_id, result])),
    [run.results],
  );

  const exportPayload = useMemo(
    () => ({
      audio_duration_sec: run.audioDurationSec,
      results: run.results,
    }),
    [run.audioDurationSec, run.results],
  );

  return (
    <section className="space-y-4">
      {run.error ? (
        <p className="rounded-xl border border-red-900/60 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {run.error}
        </p>
      ) : null}

      {run.isComplete && run.results.length > 0 ? (
        <ExportToolbar payload={exportPayload} />
      ) : null}

      <Tabs defaultValue="cards">
        <TabsList>
          <TabsTrigger value="cards">Cards</TabsTrigger>
          <TabsTrigger value="table">Table</TabsTrigger>
          <TabsTrigger value="compare">Compare</TabsTrigger>
        </TabsList>

        <TabsContent value="cards">
          <div className="masonry-grid">
            {run.providers.map((provider) => {
              const result = resultMap[provider.id];
              const status = run.providerStatus[provider.id];
              const loading =
                !result &&
                (status?.state === "pending" || status?.state === "running");

              return (
                <ResultCard
                  key={provider.id}
                  providerName={provider.display_name}
                  result={result}
                  loading={loading}
                  badges={
                    result ? badgesForResult(result.provider_id, run.results) : []
                  }
                />
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="table">
          {run.results.length > 0 ? (
            <ResultTable results={run.results} />
          ) : (
            <p className="text-sm text-zinc-500">Waiting for results…</p>
          )}
        </TabsContent>

        <TabsContent value="compare">
          <CompareView results={run.results} />
        </TabsContent>
      </Tabs>
    </section>
  );
}

export function ResultsWorkspace({ runs }: ResultsWorkspaceProps) {
  if (runs.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 px-6 py-12 text-center">
        <p className="text-sm text-zinc-500">
          Results will appear here after you transcribe audio.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {runs.map((run) => (
        <div key={run.id} className="space-y-4">
          {runs.length > 1 ? (
            <h2 className="text-lg font-medium text-zinc-200">{run.fileName}</h2>
          ) : null}
          <RunResults run={run} />
        </div>
      ))}
    </div>
  );
}
