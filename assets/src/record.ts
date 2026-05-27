type RecordControls = {
  start: () => Promise<void>;
  stop: () => void;
  isRecording: () => boolean;
};

export function initMicRecorder(
  onComplete: (file: File) => void,
  onError: (message: string) => void,
): RecordControls {
  let mediaRecorder: MediaRecorder | null = null;
  let chunks: Blob[] = [];
  let stream: MediaStream | null = null;

  async function start(): Promise<void> {
    if (mediaRecorder?.state === "recording") {
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      onError("Microphone access denied or unavailable");
      return;
    }

    chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };
    mediaRecorder.onstop = () => {
      stream?.getTracks().forEach((track) => track.stop());
      stream = null;
      const blob = new Blob(chunks, { type: mediaRecorder?.mimeType || "audio/webm" });
      const extension = blob.type.includes("webm") ? "webm" : "wav";
      onComplete(
        new File([blob], `recording-${Date.now()}.${extension}`, {
          type: blob.type || "audio/webm",
        }),
      );
      chunks = [];
      mediaRecorder = null;
    };
    mediaRecorder.start();
  }

  function stop(): void {
    if (mediaRecorder?.state === "recording") {
      mediaRecorder.stop();
    }
  }

  function isRecording(): boolean {
    return mediaRecorder?.state === "recording";
  }

  return { start, stop, isRecording };
}
