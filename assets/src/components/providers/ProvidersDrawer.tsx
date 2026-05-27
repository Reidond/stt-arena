import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Server, X } from "lucide-react";
import type { ProviderStatus } from "@/api/types";
import { ProviderPanel } from "@/components/providers/ProviderPanel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ProvidersDrawerProps = {
  providers: ProviderStatus[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
};

function providerSummary(providers: ProviderStatus[]) {
  const enabled = providers.filter((provider) => provider.enabled);
  const available = enabled.filter((provider) => provider.available);
  return { enabled: enabled.length, available: available.length };
}

export function ProvidersDrawer({
  providers,
  loading,
  error,
  onRefresh,
}: ProvidersDrawerProps) {
  const { enabled, available } = providerSummary(providers);
  const hasUnavailable = !loading && available < enabled;

  return (
    <DialogPrimitive.Root>
      <DialogPrimitive.Trigger asChild>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className={cn(
            "gap-2",
            hasUnavailable && "border-amber-900/60 text-amber-300",
          )}
        >
          <Server className="h-3.5 w-3.5" aria-hidden="true" />
          {loading ? (
            "Providers…"
          ) : (
            <>
              Providers
              <span className="text-zinc-500">·</span>
              <span className={hasUnavailable ? "text-amber-300" : "text-emerald-400"}>
                {available}/{enabled} ready
              </span>
            </>
          )}
        </Button>
      </DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/60" />
        <DialogPrimitive.Content
          className={cn(
            "fixed inset-y-0 right-0 z-50 flex w-[min(22rem,92vw)] flex-col",
            "border-l border-zinc-800 bg-zinc-950 p-5 shadow-xl outline-none",
          )}
        >
          <div className="mb-4 flex items-start justify-between gap-3 pr-8">
            <DialogPrimitive.Title className="text-lg font-medium text-zinc-100">
              Providers
            </DialogPrimitive.Title>
            <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </DialogPrimitive.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ProviderPanel
              providers={providers}
              loading={loading}
              error={error}
              onRefresh={onRefresh}
              hideHeader
            />
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
