import type { ExportPayload, ProgressiveSession, TranscriptionResult } from "./types";

async function readErrorMessage(response: Response): Promise<string> {
  const text = (await response.text()).trim();
  if (!text) {
    return "Transcription failed";
  }
  try {
    const payload = JSON.parse(text) as { detail?: string | string[] };
    if (Array.isArray(payload.detail)) {
      return payload.detail.join(", ");
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    return text;
  }
  return text;
}

export async function startProgressiveSession(
  file: File,
  language: string,
  diarization: boolean,
): Promise<ProgressiveSession> {
  const payload = new FormData();
  payload.set("file", file);
  if (language) {
    payload.set("language", language);
  }
  if (diarization) {
    payload.set("diarization", "true");
  }

  const response = await fetch("/api/transcribe", {
    method: "POST",
    body: payload,
    headers: {
      Accept: "application/json",
      "X-Progressive": "1",
    },
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as ProgressiveSession;
}

export type StreamCallbacks = {
  onResult: (result: TranscriptionResult) => void;
  onError: (message: string) => void;
  onDone: (audioDurationSec: number) => void;
};

export function openTranscriptionStream(
  sessionId: string,
  callbacks: StreamCallbacks,
): EventSource {
  const stream = new EventSource(`/api/transcribe/sessions/${sessionId}/events`);
  let finished = false;

  stream.addEventListener("result", (event) => {
    const data = JSON.parse((event as MessageEvent<string>).data) as {
      result: TranscriptionResult;
    };
    callbacks.onResult(data.result);
  });

  stream.addEventListener("error", (event) => {
    const data = JSON.parse((event as MessageEvent<string>).data) as {
      message?: string;
    };
    if (data.message) {
      finished = true;
      stream.close();
      callbacks.onError(data.message);
    }
  });

  stream.addEventListener("done", (event) => {
    finished = true;
    let audioDurationSec = 0;
    try {
      const data = JSON.parse((event as MessageEvent<string>).data) as {
        audio_duration_sec?: number;
      };
      audioDurationSec = data.audio_duration_sec ?? 0;
    } catch {
      // Ignore malformed payloads.
    }
    stream.close();
    callbacks.onDone(audioDurationSec);
  });

  stream.onerror = () => {
    if (finished) {
      return;
    }
    stream.close();
    callbacks.onError("Transcription stream failed");
  };

  return stream;
}

export type { ExportPayload };
