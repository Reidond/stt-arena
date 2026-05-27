import { useCallback, useRef, useState } from "react";
import {
  openTranscriptionStream,
  startProgressiveSession,
} from "@/api/transcribe";
import type {
  BatchRun,
  ProviderRunStatus,
  TranscriptionResult,
} from "@/api/types";

function createRunId(): string {
  return crypto.randomUUID();
}

function initialProviderStatus(
  providers: Array<{ id: string; display_name: string }>,
): Record<string, ProviderRunStatus> {
  return Object.fromEntries(
    providers.map((provider) => [provider.id, { state: "pending" as const }]),
  );
}

export function useTranscriptionStream() {
  const [runs, setRuns] = useState<BatchRun[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [liveMessage, setLiveMessage] = useState("");
  const [batchTotal, setBatchTotal] = useState(0);
  const [batchIndex, setBatchIndex] = useState(0);
  const streamRef = useRef<EventSource | null>(null);

  const cancel = useCallback(() => {
    streamRef.current?.close();
    streamRef.current = null;
    setIsRunning(false);
    setRuns((current) =>
      current.map((run) =>
        run.isComplete
          ? run
          : {
              ...run,
              isComplete: true,
              error: run.error ?? "Cancelled",
              providerStatus: Object.fromEntries(
                Object.entries(run.providerStatus).map(([id, status]) => [
                  id,
                  status.state === "pending" || status.state === "running"
                    ? { state: "error" as const, message: "Cancelled" }
                    : status,
                ]),
              ),
            },
      ),
    );
  }, []);

  const updateRun = useCallback(
    (runId: string, updater: (run: BatchRun) => BatchRun) => {
      setRuns((current) =>
        current.map((run) => (run.id === runId ? updater(run) : run)),
      );
    },
    [],
  );

  const transcribeFiles = useCallback(
    async (files: File[], language: string) => {
      streamRef.current?.close();
      setRuns([]);
      setIsRunning(true);
      setBatchTotal(files.length);
      setBatchIndex(0);
      setLiveMessage("Starting transcription…");

      for (const [index, file] of files.entries()) {
        setBatchIndex(index + 1);
        const runId = createRunId();
        let sessionProviders: Array<{ id: string; display_name: string }> = [];

        try {
          const session = await startProgressiveSession(file, language);
          sessionProviders = session.providers;

          setRuns((current) => [
            ...current,
            {
              id: runId,
              fileName: file.name,
              audioDurationSec: session.audio_duration_sec,
              providers: session.providers,
              providerStatus: initialProviderStatus(session.providers),
              results: [],
              isComplete: false,
            },
          ]);

          await new Promise<void>((resolve, reject) => {
            updateRun(runId, (run) => ({
              ...run,
              providerStatus: Object.fromEntries(
                sessionProviders.map((provider) => [
                  provider.id,
                  { state: "running" as const },
                ]),
              ),
            }));

            streamRef.current = openTranscriptionStream(session.session_id, {
              onResult: (result: TranscriptionResult) => {
                updateRun(runId, (run) => ({
                  ...run,
                  results: [...run.results, result],
                  providerStatus: {
                    ...run.providerStatus,
                    [result.provider_id]: { state: "done", result },
                  },
                }));
                setLiveMessage(
                  `${result.display_name ?? result.provider_id} finished in ${result.latency_ms} ms`,
                );
              },
              onError: (message) => {
                updateRun(runId, (run) => ({
                  ...run,
                  isComplete: true,
                  error: message,
                }));
                reject(new Error(message));
              },
              onDone: (audioDurationSec) => {
                updateRun(runId, (run) => ({
                  ...run,
                  audioDurationSec: audioDurationSec || run.audioDurationSec,
                  isComplete: true,
                }));
                resolve();
              },
            });
          });
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Transcription failed";
          setLiveMessage(message);
          if (sessionProviders.length > 0) {
            updateRun(runId, (run) => ({
              ...run,
              isComplete: true,
              error: message,
            }));
          } else {
            setRuns((current) => [
              ...current,
              {
                id: runId,
                fileName: file.name,
                audioDurationSec: 0,
                providers: [],
                providerStatus: {},
                results: [],
                isComplete: true,
                error: message,
              },
            ]);
          }
          break;
        }
      }

      streamRef.current = null;
      setIsRunning(false);
      setLiveMessage("");
    },
    [updateRun],
  );

  return {
    runs,
    isRunning,
    liveMessage,
    batchProgress: isRunning
      ? { current: batchIndex, total: batchTotal }
      : null,
    transcribeFiles,
    cancel,
  };
}
