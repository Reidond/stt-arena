function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setFormBusy(form: HTMLFormElement, busy: boolean): void {
  form.dataset.busy = busy ? "true" : "false";
  for (const element of form.elements) {
    if (
      element instanceof HTMLInputElement ||
      element instanceof HTMLButtonElement
    ) {
      element.disabled = busy;
    }
  }
}

function showError(results: HTMLElement, message: string): void {
  results.innerHTML = `<p class="text-sm text-red-400">${escapeHtml(message)}</p>`;
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

export function initTranscribeForm(): void {
  const form = document.getElementById("transcribe-form");
  const results = document.getElementById("results");
  if (!(form instanceof HTMLFormElement) || !(results instanceof HTMLElement)) {
    return;
  }

  let activeStream: EventSource | null = null;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (form.dataset.busy === "true") {
      return;
    }

    void (async () => {
      activeStream?.close();
      activeStream = null;

      const fileInput = form.querySelector('input[type="file"]');
      if (
        !(fileInput instanceof HTMLInputElement) ||
        fileInput.files === null ||
        fileInput.files.length === 0
      ) {
        showError(results, "Please select an audio file");
        return;
      }

      const payload = new FormData(form);
      setFormBusy(form, true);

      try {
        const response = await fetch("/api/transcribe", {
          method: "POST",
          body: payload,
          headers: {
            Accept: "text/html",
            "X-Progressive": "1",
          },
        });

        if (!response.ok) {
          showError(results, await readErrorMessage(response));
          setFormBusy(form, false);
          return;
        }

        results.innerHTML = await response.text();
        const streamUrl = results
          .querySelector("[data-stream-url]")
          ?.getAttribute("data-stream-url");
        if (!streamUrl) {
          setFormBusy(form, false);
          return;
        }

        activeStream = new EventSource(streamUrl);
        let streamFinished = false;

        activeStream.addEventListener("result", (streamEvent) => {
          const payload = JSON.parse((streamEvent as MessageEvent<string>).data) as {
            provider_id: string;
            html: string;
          };
          const slot = document.getElementById(`result-${payload.provider_id}`);
          if (slot) {
            slot.outerHTML = payload.html;
          }
        });

        activeStream.addEventListener("error", (streamEvent) => {
          const payload = JSON.parse((streamEvent as MessageEvent<string>).data) as {
            message?: string;
          };
          if (payload.message) {
            showError(results, payload.message);
          }
        });

        activeStream.addEventListener("done", () => {
          streamFinished = true;
          activeStream?.close();
          activeStream = null;
          setFormBusy(form, false);
        });

        activeStream.onerror = () => {
          if (streamFinished) {
            return;
          }
          activeStream?.close();
          activeStream = null;
          setFormBusy(form, false);
        };
      } catch {
        showError(results, "Request failed");
        setFormBusy(form, false);
      }
    })();
  });
}
