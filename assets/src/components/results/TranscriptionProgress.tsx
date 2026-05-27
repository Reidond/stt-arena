import type { BatchRun } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { formatLatency } from "@/lib/format";

type TranscriptionProgressProps = {
  run: BatchRun;
};

export function TranscriptionProgress({ run }: TranscriptionProgressProps) {
  const completedCount = Object.values(run.providerStatus).filter(
    (status) => status.state === "done" || status.state === "error",
  ).length;
  const totalCount = run.providers.length;
  const progressValue =
    totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium uppercase tracking-widest text-zinc-500">
          Transcribing
        </h2>
        <span className="text-sm text-zinc-300">
          {completedCount}/{totalCount} providers
        </span>
      </div>
      <Progress value={progressValue} className="mb-4" />
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {run.providers.map((provider) => {
          const status = run.providerStatus[provider.id];
          return (
            <li
              key={provider.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-950/50 px-3 py-2 text-sm"
            >
              <span className="truncate text-zinc-300">{provider.display_name}</span>
              {!status || status.state === "pending" ? (
                <Badge variant="muted">pending</Badge>
              ) : status.state === "running" ? (
                <Badge variant="default">running</Badge>
              ) : status.state === "done" ? (
                <span className="text-xs text-emerald-400">
                  {formatLatency(status.result.latency_ms)}
                </span>
              ) : (
                <Badge variant="error">error</Badge>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
