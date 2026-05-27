import { RefreshCw } from "lucide-react";
import type { ProviderStatus } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type ProviderPanelProps = {
  providers: ProviderStatus[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  compact?: boolean;
  hideHeader?: boolean;
};

function statusBadge(provider: ProviderStatus) {
  if (!provider.enabled) {
    return <Badge variant="muted">disabled</Badge>;
  }
  if (provider.available) {
    return <Badge variant="success">available</Badge>;
  }
  return <Badge variant="warning">unavailable</Badge>;
}

function ProviderItem({ provider }: { provider: ProviderStatus }) {
  return (
    <li className="rounded-xl border border-zinc-800 bg-zinc-950/60 px-3 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium text-zinc-100">{provider.display_name}</p>
          <p className="truncate text-xs text-zinc-500">{provider.id}</p>
        </div>
        {statusBadge(provider)}
      </div>
      {provider.billing ? (
        <p className="mt-2 text-xs text-zinc-500">
          {provider.billing.plan_label} · ${provider.billing.rate_usd_per_minute.toFixed(4)}/min
          {provider.billing.free_minutes_monthly > 0
            ? ` · ${provider.billing.free_minutes_monthly} free min/mo`
            : ""}
        </p>
      ) : null}
      {provider.reason ? (
        <p className="mt-2 text-xs text-zinc-500">{provider.reason}</p>
      ) : null}
    </li>
  );
}

export function ProviderPanel({
  providers,
  loading,
  error,
  onRefresh,
  compact = false,
  hideHeader = false,
}: ProviderPanelProps) {
  const enabled = providers.filter((p) => p.enabled);
  const available = enabled.filter((p) => p.available);

  return (
    <div className={compact ? "space-y-3" : "space-y-4"}>
      {hideHeader ? (
        <div className="flex justify-end">
          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            disabled={loading}
            aria-label="Refresh providers"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-medium uppercase tracking-widest text-zinc-500">
              Providers
            </h2>
            {!loading ? (
              <p className="mt-1 text-xs text-zinc-500">
                {available.length} of {enabled.length} ready
              </p>
            ) : null}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            disabled={loading}
            aria-label="Refresh providers"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      )}

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : (
        <ul className="space-y-2">
          {providers.map((provider) => (
            <ProviderItem key={provider.id} provider={provider} />
          ))}
        </ul>
      )}
    </div>
  );
}
