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
            <p className="text-sm font-medium uppercase tracking-widest text-emerald-400">
              Local-first STT benchmark
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white lg:text-4xl">
              stt-arena
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-zinc-400 lg:text-base">
              Upload audio and compare transcription results across providers in
              parallel.
            </p>
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
