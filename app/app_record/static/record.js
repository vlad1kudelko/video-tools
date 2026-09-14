const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const IDLE_STATE = { status: "idle", message: "—", progress: 0 };

export function RecordTab() {
  const [url, setUrl] = useState("");
  const [w, setW] = useState(1080);
  const [h_, setH] = useState(1920);
  const [scrollSpeed, setScrollSpeed] = useState(360);
  const [maxSeconds, setMaxSeconds] = useState(60);
  const [jobId, setJobId] = useState(null);
  const [state, setState] = useState(IDLE_STATE);
  const [busy, setBusy] = useState(false);

  const swap = () => { setW(h_); setH(w); };

  const start = async () => {
    if (!url.trim()) return;
    setBusy(true);
    setJobId(null);
    setState({ status: "processing", message: "Загрузка…", progress: 0 });

    const fd = new FormData();
    fd.append("url", url.trim());
    fd.append("width", w);
    fd.append("height", h_);
    fd.append("scroll_speed", scrollSpeed);
    fd.append("max_seconds", maxSeconds);
    const r = await fetch("/api/record/start", { method: "POST", body: fd });
    if (!r.ok) {
      setState({ status: "error", message: "Ошибка запроса", progress: 0 });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    setJobId(id);
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/record/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setState(j);
      if (j.status !== "processing") setBusy(false);
    };
  };

  const pct = state.status === "done" ? 100 : Math.round(state.progress * 100);

  return html`
    <h1 class="mb-6 text-lg font-semibold">Запись экрана</h1>

    <label class="mb-5 block text-sm">
      <span class="mb-1 block text-neutral-400">Ссылка на сайт</span>
      <input type="text" value=${url} onInput=${e => setUrl(e.target.value)}
        placeholder="https://example.com"
        class="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
    </label>

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
        <input type="number" min="2" value=${h_} onInput=${e => setH(+e.target.value)}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>
    </div>

    <div class="mb-5 flex items-end gap-3">
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Скорость прокрутки, px/сек</span>
        <input type="number" min="1" value=${scrollSpeed} onInput=${e => setScrollSpeed(+e.target.value)}
          class="w-36 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Макс. длительность, сек</span>
        <input type="number" min="1" value=${maxSeconds} onInput=${e => setMaxSeconds(+e.target.value)}
          class="w-36 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
      </label>
    </div>

    <button onClick=${start} disabled=${!url.trim() || busy}
      class="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Записать
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

    <button disabled=${state.status !== "done"} onClick=${() => { window.location.href = `/api/record/${jobId}/file`; }}
      class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать результат
    </button>
  `;
}
