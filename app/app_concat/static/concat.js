import { DropZone } from "/dropzone.js";

const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const TRANSITIONS = [
  { id: "none", label: "Без перехода", preview: null },
  { id: "fade", label: "Плавное перетекание" },
  { id: "wipeleft", label: "Шторка влево" },
  { id: "wiperight", label: "Шторка вправо" },
  { id: "wipeup", label: "Шторка вверх" },
  { id: "wipedown", label: "Шторка вниз" },
  { id: "slideleft", label: "Сдвиг влево" },
  { id: "slideright", label: "Сдвиг вправо" },
  { id: "slideup", label: "Сдвиг вверх" },
  { id: "slidedown", label: "Сдвиг вниз" },
  { id: "circlecrop", label: "Круг (обрезка)" },
  { id: "rectcrop", label: "Прямоугольник (обрезка)" },
  { id: "distance", label: "Дистанция" },
  { id: "fadeblack", label: "Через чёрный" },
  { id: "fadewhite", label: "Через белый" },
  { id: "radial", label: "Радиальный" },
  { id: "smoothleft", label: "Плавно влево" },
  { id: "smoothright", label: "Плавно вправо" },
  { id: "smoothup", label: "Плавно вверх" },
  { id: "smoothdown", label: "Плавно вниз" },
  { id: "circleopen", label: "Круг (открытие)" },
  { id: "circleclose", label: "Круг (закрытие)" },
  { id: "vertopen", label: "Открытие по вертикали" },
  { id: "vertclose", label: "Закрытие по вертикали" },
  { id: "horzopen", label: "Открытие по горизонтали" },
  { id: "horzclose", label: "Закрытие по горизонтали" },
  { id: "dissolve", label: "Растворение" },
  { id: "diagtl", label: "Диагональ ↖" },
  { id: "diagtr", label: "Диагональ ↗" },
  { id: "diagbl", label: "Диагональ ↙" },
  { id: "diagbr", label: "Диагональ ↘" },
  { id: "hlslice", label: "Полосы слева" },
  { id: "hrslice", label: "Полосы справа" },
  { id: "vuslice", label: "Полосы снизу" },
  { id: "vdslice", label: "Полосы сверху" },
  { id: "fadegrays", label: "Через чёрно-белое" },
  { id: "wipetl", label: "Шторка из угла ↖" },
  { id: "wipetr", label: "Шторка из угла ↗" },
  { id: "wipebl", label: "Шторка из угла ↙" },
  { id: "wipebr", label: "Шторка из угла ↘" },
  { id: "squeezeh", label: "Сжатие по горизонтали" },
  { id: "squeezev", label: "Сжатие по вертикали" },
].map(t => ({ ...t, preview: t.preview === null ? null : `${t.id}.gif` }));

function TransitionTile({ item, selected, onSelect }) {
  return html`
    <button type="button" onClick=${onSelect}
      class=${"flex flex-col items-stretch overflow-hidden rounded-lg border text-center transition " +
        (selected ? "border-indigo-500 ring-1 ring-indigo-500" : "border-neutral-700 hover:border-neutral-500")}>
      ${item.preview
        ? html`<img src=${`/concat-static/previews/${item.preview}`} class="aspect-video w-full shrink-0 bg-neutral-900 object-cover" />`
        : html`<div class="flex aspect-video w-full shrink-0 items-center justify-center bg-neutral-900 text-lg text-neutral-500">✂</div>`}
      <div class="px-1 py-1 text-[11px] text-neutral-300">${item.label}</div>
    </button>`;
}

const IDLE_STATE = { status: "idle", message: "—", progress: 0 };

export function ConcatTab() {
  const [files, setFiles] = useState([]);
  const [transition, setTransition] = useState("fade");
  const [duration, setDuration] = useState(0.5);
  const [jobId, setJobId] = useState(null);
  const [state, setState] = useState(IDLE_STATE);
  const [busy, setBusy] = useState(false);

  const start = async () => {
    const file = files[0];
    if (!file) return;
    setBusy(true);
    setJobId(null);
    setState({ ...IDLE_STATE, status: "processing", message: "Загрузка архива…" });

    const fd = new FormData();
    fd.append("file", file);
    fd.append("transition", transition);
    fd.append("transition_duration", duration);
    const r = await fetch("/api/concat/start", { method: "POST", body: fd });
    if (!r.ok) {
      setState({ ...IDLE_STATE, status: "error", message: "Ошибка запроса" });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    setJobId(id);
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/concat/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setState(j);
      if (j.status !== "processing") setBusy(false);
    };
  };

  const pct = state.status === "done" ? 100 : Math.round(state.progress * 100);

  return html`
    <h1 class="mb-6 text-lg font-semibold">Склейка видео</h1>

    <${DropZone} multiple=${false} accept=".zip" files=${files} onFiles=${setFiles}
      hint="Перетащите zip-архив с видео сюда или нажмите, чтобы выбрать" />

    <div class="mt-5">
      <span class="mb-2 block text-sm text-neutral-400">Переход</span>
      <div class="grid grid-cols-4 gap-2 sm:grid-cols-8">
        ${TRANSITIONS.map(t => html`<${TransitionTile} key=${t.id} item=${t} selected=${transition === t.id} onSelect=${() => setTransition(t.id)} />`)}
      </div>
    </div>

    <label class="mt-5 block text-sm">
      <span class="mb-1 block text-neutral-400">Длительность перехода, сек</span>
      <input type="number" min="0.1" step="0.1" value=${duration} onInput=${e => setDuration(+e.target.value)}
        class="w-32 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
    </label>

    <button onClick=${start} disabled=${!files.length || busy}
      class="mt-5 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Склеить
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

    <button disabled=${state.status !== "done"} onClick=${() => { window.location.href = `/api/concat/${jobId}/file`; }}
      class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать результат
    </button>
  `;
}
