import { useCallback, useEffect, useRef, useState } from "react";

type UseAudioRecorderOptions = {
  maxDurationSec?: number;
  onComplete: (file: File) => void;
  onError: (message: string) => void;
};

export function useAudioRecorder({
  maxDurationSec = 300,
  onComplete,
  onError,
}: UseAudioRecorderOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [level, setLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  const cleanup = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    analyserRef.current = null;
    setLevel(0);
  }, []);

  const stop = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const discard = useCallback(() => {
    cleanup();
    chunksRef.current = [];
    mediaRecorderRef.current = null;
    setIsRecording(false);
    setElapsedSec(0);
  }, [cleanup]);

  const start = useCallback(async () => {
    if (mediaRecorderRef.current?.state === "recording") {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((sum, value) => sum + value, 0) / data.length;
        setLevel(Math.min(1, avg / 128));
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);

      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        cleanup();
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        const extension = blob.type.includes("webm") ? "webm" : "wav";
        onComplete(
          new File([blob], `recording-${Date.now()}.${extension}`, {
            type: blob.type || "audio/webm",
          }),
        );
        chunksRef.current = [];
        mediaRecorderRef.current = null;
        setIsRecording(false);
        setElapsedSec(0);
      };

      recorder.start();
      setIsRecording(true);
      setElapsedSec(0);
      timerRef.current = window.setInterval(() => {
        setElapsedSec((prev) => {
          const next = prev + 1;
          if (next >= maxDurationSec) {
            stop();
          }
          return next;
        });
      }, 1000);
    } catch {
      cleanup();
      onError("Microphone access denied or unavailable");
    }
  }, [cleanup, maxDurationSec, onComplete, onError, stop]);

  useEffect(() => () => cleanup(), [cleanup]);

  return {
    isRecording,
    elapsedSec,
    level,
    maxDurationSec,
    start,
    stop,
    discard,
  };
}
