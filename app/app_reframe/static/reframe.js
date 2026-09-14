import { DropZone } from "/dropzone.js";
import { uploadWithProgress } from "/upload.js";

const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const TITLES = { blur: "Из маленького — в большое", crop: "Из большого — в маленькое" };
const GRAVITY_CELLS = [null, "top", null, "left", "center", "right", null, "bottom", null];
const GRAVITY_ARROWS = { top: "↑", left: "←", center: "•", right: "→", bottom: "↓" };

const segClass = on =>
  "rounded-lg px-3 py-2 text-sm font-medium transition " +
  (on ? "bg-indigo-600/20 text-indigo-300 ring-1 ring-inset ring-indigo-500/40" : "text-neutral-400 hover:bg-neutral-900");

const gravityClass = on =>
  "flex h-11 items-center justify-center rounded-lg border text-base transition " +
  (on ? "border-indigo-500 bg-indigo-600/20 text-indigo-300" : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-500");

export function ReframeTab() {
  const [mode, setMode] = useState("blur");
  const [gravity, setGravity] = useState("center");
  const [w, setW] = useState(1080);
  const [ht, setHt] = useState(1920);
  const [duration, setDuration] = useState(3);
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState({ text: "—", pct: 0 });
  const [busy, setBusy] = useState(false);
  const [resultId, setResultId] = useState(null);

  const swap = () => { setW(ht); setHt(w); };

  const submit = async () => {
    setBusy(true);
    setResultId(null);
    setStatus({ text: "Загрузка файлов…", pct: 0 });
    const fd = new FormData();
    fd.append("width", w);
    fd.append("height", ht);
    fd.append("mode", mode);
    fd.append("gravity", gravity);
    fd.append("duration", duration);
    files.forEach(f => fd.append("files", f));
    const r = await uploadWithProgress("/api/jobs", fd,
      frac => setStatus({ text: "Загрузка файлов…", pct: Math.round(frac * 100) }));
    if (!r.ok) {
      setStatus({ text: "Ошибка запроса", pct: 0 });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      if (j.status === "processing") {
        setStatus({
          text: `Обработка ${Math.min(j.done + 1, j.total)} / ${j.total}`,
          pct: Math.round(((j.done + j.progress) / j.total) * 100),
        });
      } else if (j.status === "done") {
        setStatus({ text: "Готово", pct: 100 });
        setResultId(id);
        setBusy(false);
      } else {
        setStatus({ text: "Ошибка: " + (j.message || "неизвестно"), pct: 0 });
        setBusy(false);
      }
    };
  };

  return html`
    <h1 class="mb-6 text-lg font-semibold">${TITLES[mode]}</h1>

    <div class="mb-5 inline-flex gap-1 rounded-lg border border-neutral-700 p-1">
      <button class=${segClass(mode === "blur")} onClick=${() => setMode("blur")}>Размытый фон</button>
      <button class=${segClass(mode === "crop")} onClick=${() => setMode("crop")}>Обрезка (cover)</button>
    </div>

    <div class="mb-5 flex items-end gap-3">
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Ширина</span>
        <input type="number" min="2" value=${w} onInput=${e => setW(+e.target.value)}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>
      <button title="Поменять Ш и В местами" onClick=${swap}
        class="mb-[1px] rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-400 transition hover:border-neutral-500 hover:text-neutral-200">⇄</button>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Высота</span>
        <input type="number" min="2" value=${ht} onInput=${e => setHt(+e.target.value)}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Длительность для картинок, сек</span>
        <input type="number" min="0.1" step="0.1" value=${duration} onInput=${e => setDuration(+e.target.value)}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>
    </div>

    ${mode === "crop" && html`
      <div class="mb-5">
        <span class="mb-2 block text-sm text-neutral-400">Прижать при обрезке</span>
        <div class="grid w-[136px] grid-cols-3 gap-1">
          ${GRAVITY_CELLS.map((g, i) => g
            ? html`<button key=${g} class=${gravityClass(gravity === g)} onClick=${() => setGravity(g)}>${GRAVITY_ARROWS[g]}</button>`
            : html`<span key=${"e" + i}></span>`)}
        </div>
      </div>
    `}

    <${DropZone} multiple=${true} accept="video/*,image/*,.zip" files=${files} onFiles=${setFiles}
      hint="Перетащите видео, картинки, гифки или zip-архив сюда или нажмите, чтобы выбрать" />

    <button disabled=${!files.length || busy} onClick=${submit}
      class="mt-5 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Обработать
    </button>

    <div class="mt-6">
      <div class="mb-2 flex justify-between text-xs text-neutral-400">
        <span>${status.text}</span><span>${status.pct == null ? "" : status.pct + "%"}</span>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
        <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: (status.pct ?? 0) + "%" }}></div>
      </div>
    </div>

    <button disabled=${!resultId} onClick=${() => { window.location.href = `/api/jobs/${resultId}/download`; }}
      class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать результат
    </button>
  `;
}
