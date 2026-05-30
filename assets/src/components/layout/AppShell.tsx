import type { ReactNode } from "react";

type AppShellProps = {
  headerActions?: ReactNode;
  children: ReactNode;
};

export function AppShell({ headerActions, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-zinc-950">
      <div className="mx-auto max-w-6xl px-4 py-8 lg:px-6 lg:py-10">
        <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
              STT Arena
            </h1>
          </div>
          {headerActions ? (
            <div className="flex shrink-0 items-center gap-2">{headerActions}</div>
          ) : null}
        </header>

        <main className="space-y-6">{children}</main>
      </div>
    </div>
  );
}
