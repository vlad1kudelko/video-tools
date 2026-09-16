import { DropZone } from "/dropzone.js";
import { TransitionPicker } from "/transition-picker.js";
import { uploadWithProgress, combinedPct } from "/upload.js";

const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const IDLE_STATE = { status: "idle", message: "—", progress: 0 };

function Block({ index, files, onFiles, onRemove, removable, repeat, onRepeatChange }) {
  return html`
    <div class="mb-4 rounded-lg border border-neutral-800 p-3">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium text-neutral-300">Блок ${index + 1}</span>
        <button type="button" onClick=${onRemove} disabled=${!removable}
          class="text-xs text-neutral-500 hover:text-neutral-300 disabled:cursor-not-allowed disabled:opacity-30">✕ убрать</button>
      </div>
      <${DropZone} multiple=${true} accept="video/*,image/*,.zip" files=${files} onFiles=${onFiles}
        hint="Медиа или zip-архив для этого блока" />
      <label class="mt-2 flex items-center gap-2 text-sm">
        <span class="text-neutral-400">Повторений</span>
        <input type="number" min="1" value=${repeat} onInput=${e => onRepeatChange(+e.target.value)}
          class="w-20 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1.5 outline-none focus:border-indigo-500" />
      </label>
    </div>`;
}

export function CombinatorTab() {
  const [blocks, setBlocks] = useState([{ files: [], repeat: 1 }]); // one entry per block
  const [transition, setTransition] = useState("fade");
  const [duration, setDuration] = useState(0.5);
  const [jobId, setJobId] = useState(null);
  const [state, setState] = useState(IDLE_STATE);
  const [uploadFrac, setUploadFrac] = useState(0);
  const [busy, setBusy] = useState(false);

  const setBlockCount = n => setBlocks(prev => {
    n = Math.max(1, Math.floor(n) || 1);
    if (n === prev.length) return prev;
    if (n > prev.length) return [...prev, ...Array.from({ length: n - prev.length }, () => ({ files: [], repeat: 1 }))];
    return prev.slice(0, n);
  });

  const addBlock = () => setBlocks(prev => [...prev, { files: [], repeat: 1 }]);
  const removeBlock = i => setBlocks(prev => prev.length > 1 ? prev.filter((_, idx) => idx !== i) : prev);
  const setBlockFiles = (i, files) => setBlocks(prev => prev.map((b, idx) => idx === i ? { ...b, files } : b));
  const setBlockRepeat = (i, repeat) => setBlocks(prev => prev.map((b, idx) => idx === i ? { ...b, repeat: Math.max(1, Math.floor(repeat) || 1) } : b));

  const canGenerate = blocks.every(b => b.files.length > 0) && !busy;

  const generate = async () => {
    if (!canGenerate) return;
    setBusy(true);
    setJobId(null);
    setUploadFrac(0);
    setState({ ...IDLE_STATE, status: "processing", message: "Загрузка…" });

    const fd = new FormData();
    blocks.forEach(({ files }, i) => files.forEach(f => {
      fd.append("files", f);
      fd.append("blocks", String(i));
    }));
    blocks.forEach(({ repeat }) => fd.append("repeats", String(repeat)));
    fd.append("transition", transition);
    fd.append("transition_duration", duration);

    const r = await uploadWithProgress("/api/combinator/generate", fd, setUploadFrac);
    if (!r.ok) {
      setState({ ...IDLE_STATE, status: "error", message: "Ошибка запроса" });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    setJobId(id);
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/combinator/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setState(j);
      if (j.status !== "processing") setBusy(false);
    };
  };

  const pct = !jobId ? combinedPct(uploadFrac, 0) : combinedPct(1, state.status === "done" ? 1 : state.progress);

  return html`
    <h1 class="mb-6 text-lg font-semibold">Комбинатор</h1>

    <label class="mb-5 block text-sm">
      <span class="mb-1 block text-neutral-400">Количество блоков</span>
      <input type="number" min="1" value=${blocks.length} onInput=${e => setBlockCount(+e.target.value)}
        class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
    </label>

    ${blocks.map(({ files, repeat }, i) => html`<${Block} key=${i} index=${i} files=${files} repeat=${repeat}
      onFiles=${f => setBlockFiles(i, f)} onRemove=${() => removeBlock(i)} removable=${blocks.length > 1}
      onRepeatChange=${r => setBlockRepeat(i, r)} />`)}

    <button type="button" onClick=${addBlock}
      class="mb-5 w-full rounded-lg border border-dashed border-neutral-700 px-4 py-2 text-sm text-neutral-400 transition hover:border-neutral-500 hover:text-neutral-200">
      + Добавить блок
    </button>

    <${TransitionPicker} value=${transition} onChange=${setTransition} />

    <label class="mt-5 block text-sm">
      <span class="mb-1 block text-neutral-400">Длительность перехода, сек</span>
      <input type="number" min="0.1" step="0.1" value=${duration} onInput=${e => setDuration(+e.target.value)}
        class="w-32 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
    </label>

    <button onClick=${generate} disabled=${!canGenerate}
      class="mt-5 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Сгенерировать
    </button>

    <div class="mt-6">
      <div class="mb-2 flex justify-between text-xs text-neutral-400">
        <span>${state.status === "error" ? "Ошибка: " + (state.message || "неизвестно") : (state.message || "—")}</span>
        <span>${pct}%</span>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
        <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: pct + "%" }}></div>
      </div>
    </div>

    <button disabled=${state.status !== "done"} onClick=${() => {
      window.location.href = `/api/combinator/${jobId}/file`;
      setJobId(null);
      setUploadFrac(0);
      setState(IDLE_STATE);
    }}
      class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать результат
    </button>
  `;
}
