import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { AudioInputPanel } from "@/components/audio/AudioInputPanel";
import { ProvidersDrawer } from "@/components/providers/ProvidersDrawer";
import { ResultsWorkspace } from "@/components/results/ResultsWorkspace";
import { TranscriptionProgress } from "@/components/results/TranscriptionProgress";
import { useProviders } from "@/hooks/useProviders";
import { useTranscriptionStream } from "@/hooks/useTranscriptionStream";

export function App() {
  const { providers, languages, loading, error, refresh } = useProviders();
  const { runs, isRunning, liveMessage, batchProgress, transcribeFiles, cancel } =
    useTranscriptionStream();
  const [language, setLanguage] = useState("");
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const activeRun = useMemo(() => {
    if (!isRunning) {
      return null;
    }
    return runs.find((run) => !run.isComplete) ?? runs[runs.length - 1] ?? null;
  }, [isRunning, runs]);

  const handleSubmit = (files: File[]) => {
    setFormError(null);
    void transcribeFiles(files, language, diarizationEnabled);
  };

  return (
    <AppShell
      headerActions={
        <ProvidersDrawer
          providers={providers}
          loading={loading}
          error={error}
          onRefresh={() => void refresh()}
        />
      }
    >
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 lg:p-8">
        <h2 className="mb-4 text-sm font-medium uppercase tracking-widest text-zinc-500">
          Audio input
        </h2>
        <AudioInputPanel
          disabled={isRunning}
          isRunning={isRunning}
          batchProgress={batchProgress}
          language={language}
          languages={languages}
          diarizationEnabled={diarizationEnabled}
          onLanguageChange={setLanguage}
          onDiarizationChange={setDiarizationEnabled}
          onSubmit={handleSubmit}
          onCancel={cancel}
          onError={setFormError}
        />
        {formError ? (
          <p className="mt-3 text-sm text-red-400" role="alert">
            {formError}
          </p>
        ) : null}
      </section>

      {isRunning && activeRun ? <TranscriptionProgress run={activeRun} /> : null}

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {liveMessage}
      </div>

      <ResultsWorkspace runs={runs} />
    </AppShell>
  );
}
