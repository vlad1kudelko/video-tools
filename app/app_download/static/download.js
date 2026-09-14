import { DropZone } from "/dropzone.js";

const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const IDLE_STATE = { status: "idle", message: "—", total: 0, done: 0, current_name: "", current_progress: 0, skipped_youtube: [], filename: "" };

export function DownloadTab() {
  const [files, setFiles] = useState([]);
  const [jobId, setJobId] = useState(null);
  const [state, setState] = useState(IDLE_STATE);
  const [busy, setBusy] = useState(false);

  const start = async () => {
    const file = files[0];
    if (!file) return;
    setBusy(true);
    setJobId(null);
    setState({ ...IDLE_STATE, status: "processing", message: "Загрузка файла…" });

    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/downloads/start", { method: "POST", body: fd });
    if (!r.ok) {
      setState({ ...IDLE_STATE, status: "error", message: "Ошибка запроса" });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    setJobId(id);
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/downloads/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setState(j);
      if (j.status !== "processing") setBusy(false);
    };
  };

  const overallPct = state.total ? Math.round((state.done / state.total) * 100) : 0;
  const currentPct = Math.round(state.current_progress * 100);

  return html`
    <h1 class="mb-6 text-lg font-semibold">Скачивание медиа</h1>

    <${DropZone} multiple=${false} accept=".txt,text/plain" files=${files} onFiles=${setFiles}
      hint="Перетащите файл со ссылками сюда или нажмите, чтобы выбрать" />

    <button onClick=${start} disabled=${!files.length || busy}
      class="mt-5 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать
    </button>

    <div class="mt-6 space-y-4">
      <div>
        <div class="mb-2 flex justify-between text-xs text-neutral-400">
          <span>${state.status === "error" ? "Ошибка: " + (state.message || "неизвестно") : (state.message || "—")}</span>
          <span>${state.total ? `${state.done} из ${state.total}` : ""}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
          <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: overallPct + "%" }}></div>
        </div>
      </div>

      <div>
        <div class="mb-2 flex justify-between text-xs text-neutral-400">
          <span>${state.current_name || "—"}</span><span>${currentPct}%</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
          <div class="h-full bg-indigo-400 transition-all duration-150" style=${{ width: currentPct + "%" }}></div>
        </div>
      </div>

      <div class="text-sm text-neutral-400">Пропущено YouTube-ссылок: ${state.skipped_youtube.length}</div>
    </div>

    <button disabled=${state.status !== "done"} onClick=${() => { window.location.href = `/api/downloads/${jobId}/file`; }}
      class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать результат
    </button>
  `;
}
