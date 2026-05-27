import {
  downloadCsv,
  downloadJson,
  formatTotalCost,
  type ExportPayload,
  type ExportResult,
} from "./export";
import { initMicRecorder } from "./record";
import { initWaveform } from "./waveform";

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setFormBusy(form: HTMLFormElement, busy: boolean): void {
  form.dataset.busy = busy ? "true" : "false";
  const dropzone = document.getElementById("upload-dropzone");
  if (dropzone instanceof HTMLElement) {
    dropzone.dataset.busy = busy ? "true" : "false";
  }
  for (const element of form.elements) {
    if (
      element instanceof HTMLInputElement ||
      element instanceof HTMLButtonElement ||
      element instanceof HTMLSelectElement
    ) {
      element.disabled = busy;
    }
  }
}

function showError(container: HTMLElement, message: string): void {
  container.innerHTML = `<p class="text-sm text-red-400">${escapeHtml(message)}</p>`;
}

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

function setSelectedFileLabel(form: HTMLFormElement, label: string): void {
  const element = document.getElementById("selected-file-name");
  if (element) {
    element.textContent = label;
  }
}

function assignFilesToInput(
  fileInput: HTMLInputElement,
  files: FileList | File[],
  form: HTMLFormElement,
): void {
  const transfer = new DataTransfer();
  for (const file of files) {
    transfer.items.add(file);
  }
  fileInput.files = transfer.files;
  if (files.length === 1) {
    setSelectedFileLabel(form, files[0]?.name ?? "No file selected");
  } else if (files.length > 1) {
    setSelectedFileLabel(form, `${files.length} files selected`);
  } else {
    setSelectedFileLabel(form, "No file selected");
  }
}

function isAudioFile(file: File): boolean {
  if (file.type.startsWith("audio/") || file.type === "video/webm") {
    return true;
  }
  const extension = file.name.split(".").pop()?.toLowerCase();
  return ["wav", "mp3", "webm", "ogg", "m4a", "mp4", "mpeg", "mpga"].includes(
    extension ?? "",
  );
}

function showExportBar(
  resultsRoot: HTMLElement,
  payload: ExportPayload,
): void {
  document.getElementById("export-bar")?.remove();

  const bar = document.createElement("div");
  bar.id = "export-bar";
  bar.className =
    "mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4";
  bar.innerHTML = `
    <span class="text-sm text-zinc-400">Export results</span>
    <button type="button" data-export="json" class="rounded-md bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-700">JSON</button>
    <button type="button" data-export="csv" class="rounded-md bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-700">CSV</button>
    <span class="text-xs text-zinc-600">Costs use configured billing plans.</span>
  `;
  bar.querySelector('[data-export="json"]')?.addEventListener("click", () => {
    downloadJson(payload);
  });
  bar.querySelector('[data-export="csv"]')?.addEventListener("click", () => {
    downloadCsv(payload);
  });
  resultsRoot.prepend(bar);
}

async function previewWaveform(
  drawFile: (file: File) => Promise<void>,
  file: File,
): Promise<void> {
  await drawFile(file);
}

function initUploadDropzone(
  form: HTMLFormElement,
  results: HTMLElement,
  drawFile: (file: File) => Promise<void>,
  clearWaveform: () => void,
): void {
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = form.querySelector('input[type="file"]');
  if (!(dropzone instanceof HTMLElement) || !(fileInput instanceof HTMLInputElement)) {
    return;
  }

  fileInput.addEventListener("change", () => {
    const files = fileInput.files;
    if (!files || files.length === 0) {
      setSelectedFileLabel(form, "No file selected");
      clearWaveform();
      return;
    }
    if (files.length === 1 && files[0]) {
      void previewWaveform(drawFile, files[0]);
    } else {
      clearWaveform();
    }
    if (files.length === 1) {
      setSelectedFileLabel(form, files[0]?.name ?? "No file selected");
    } else {
      setSelectedFileLabel(form, `${files.length} files selected`);
    }
  });

  dropzone.addEventListener("click", (event) => {
    if (form.dataset.busy === "true") {
      return;
    }
    const target = event.target;
    if (
      target instanceof HTMLElement &&
      target.closest("button, input, label, a, canvas")
    ) {
      return;
    }
    fileInput.click();
  });

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (form.dataset.busy === "true") {
      return;
    }
    dropzone.classList.add("upload-dropzone--active");
  });

  dropzone.addEventListener("dragleave", (event) => {
    if (event.currentTarget === dropzone) {
      dropzone.classList.remove("upload-dropzone--active");
    }
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("upload-dropzone--active");
    if (form.dataset.busy === "true") {
      return;
    }

    const dropped = event.dataTransfer?.files;
    if (!dropped || dropped.length === 0) {
      return;
    }

    const files = Array.from(dropped).filter(isAudioFile);
    if (files.length === 0) {
      showError(
        results,
        "Unsupported audio format. Use WAV, MP3, WebM, OGG, or M4A.",
      );
      return;
    }

    assignFilesToInput(fileInput, files, form);
    if (files.length === 1 && files[0]) {
      void previewWaveform(drawFile, files[0]);
    } else {
      clearWaveform();
    }
  });
}

async function transcribeSingleFile(
  form: HTMLFormElement,
  file: File,
  target: HTMLElement,
): Promise<ExportPayload> {
  const payload = new FormData(form);
  payload.set("file", file);

  const response = await fetch("/api/transcribe", {
    method: "POST",
    body: payload,
    headers: {
      Accept: "text/html",
      "X-Progressive": "1",
    },
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  target.innerHTML = await response.text();
  const streamUrl = target
    .querySelector("[data-stream-url]")
    ?.getAttribute("data-stream-url");
  if (!streamUrl) {
    throw new Error("Missing transcription stream URL");
  }

  return await new Promise((resolve, reject) => {
    const stream = new EventSource(streamUrl);
    const collected: ExportResult[] = [];
    let durationSec = 0;
    let finished = false;

    stream.addEventListener("result", (streamEvent) => {
      const data = JSON.parse((streamEvent as MessageEvent<string>).data) as {
        provider_id: string;
        html: string;
        result: ExportResult;
      };
      const slot = document.getElementById(`result-${data.provider_id}`);
      if (slot) {
        slot.outerHTML = data.html;
      }
      collected.push(data.result);
    });

    stream.addEventListener("error", (streamEvent) => {
      const data = JSON.parse((streamEvent as MessageEvent<string>).data) as {
        message?: string;
      };
      if (data.message) {
        reject(new Error(data.message));
      }
    });

    stream.addEventListener("done", (streamEvent) => {
      finished = true;
      try {
        const data = JSON.parse((streamEvent as MessageEvent<string>).data) as {
          audio_duration_sec?: number;
        };
        durationSec = data.audio_duration_sec ?? durationSec;
      } catch {
        // Ignore malformed done payloads.
      }
      stream.close();
      resolve({ audio_duration_sec: durationSec, results: collected });
    });

    stream.onerror = () => {
      if (finished) {
        return;
      }
      stream.close();
      reject(new Error("Transcription stream failed"));
    };
  });
}

export function initTranscribeForm(): void {
  const form = document.getElementById("transcribe-form");
  const results = document.getElementById("results");
  if (!(form instanceof HTMLFormElement) || !(results instanceof HTMLElement)) {
    return;
  }

  const { drawFile, clear: clearWaveform } = initWaveform("audio-waveform");
  initUploadDropzone(form, results, drawFile, clearWaveform);

  const recordButton = document.getElementById("record-button");
  const recorder = initMicRecorder(
    (file) => {
      const fileInput = form.querySelector('input[type="file"]');
      if (fileInput instanceof HTMLInputElement) {
        assignFilesToInput(fileInput, [file], form);
        void previewWaveform(drawFile, file);
      }
      if (recordButton instanceof HTMLButtonElement) {
        recordButton.textContent = "Record";
        recordButton.dataset.recording = "false";
      }
    },
    (message) => showError(results, message),
  );

  recordButton?.addEventListener("click", () => {
    if (form.dataset.busy === "true") {
      return;
    }
    if (!(recordButton instanceof HTMLButtonElement)) {
      return;
    }
    if (recorder.isRecording()) {
      recorder.stop();
      return;
    }
    recordButton.textContent = "Stop";
    recordButton.dataset.recording = "true";
    void recorder.start();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (form.dataset.busy === "true") {
      return;
    }

    void (async () => {
      const fileInput = form.querySelector('input[type="file"]');
      if (
        !(fileInput instanceof HTMLInputElement) ||
        !fileInput.files ||
        fileInput.files.length === 0
      ) {
        showError(results, "Please select an audio file");
        return;
      }

      const files = Array.from(fileInput.files);
      setFormBusy(form, true);
      results.innerHTML = "";
      document.getElementById("export-bar")?.remove();

      const combinedResults: ExportResult[] = [];
      let totalDuration = 0;

      try {
        for (const file of files) {
          const runShell = document.createElement("section");
          runShell.className = "batch-run mb-8";
          if (files.length > 1) {
            const heading = document.createElement("h2");
            heading.className = "mb-4 text-lg font-medium text-zinc-200";
            heading.textContent = file.name;
            runShell.appendChild(heading);
          }

          const runResults = document.createElement("div");
          runResults.className =
            "batch-run__content columns-1 gap-4 lg:columns-2 xl:columns-3";
          runShell.appendChild(runResults);
          results.appendChild(runShell);

          const payload = await transcribeSingleFile(form, file, runResults);
          totalDuration += payload.audio_duration_sec;
          combinedResults.push(...payload.results);
        }

        showExportBar(results, {
          audio_duration_sec: totalDuration,
          results: combinedResults,
        });
        const exportBar = document.getElementById("export-bar");
        if (exportBar) {
          const total = document.createElement("span");
          total.className = "text-sm font-medium text-zinc-200";
          total.textContent = `Total: ${formatTotalCost(combinedResults)}`;
          exportBar.appendChild(total);
        }
      } catch (error) {
        showError(
          results,
          error instanceof Error ? error.message : "Transcription failed",
        );
      } finally {
        setFormBusy(form, false);
        if (recordButton instanceof HTMLButtonElement) {
          recordButton.textContent = "Record";
          recordButton.dataset.recording = "false";
        }
      }
    })();
  });
}
