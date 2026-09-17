import { DropZone } from "/dropzone.js";
import { uploadWithProgress, combinedPct } from "/upload.js";

const { h } = preact;
const { useState, useEffect } = preactHooks;
const html = htm.bind(h);

const IDLE_STATE = { status: "idle", message: "", current_file: "", pass_number: 0 };

function Block({ index, files, onFiles, onRemove, removable, count, onCountChange }) {
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
        <span class="text-neutral-400">Количество в проходе</span>
        <input type="number" min="1" value=${count} onInput=${e => onCountChange(+e.target.value)}
          class="w-20 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1.5 outline-none focus:border-indigo-500" />
      </label>
    </div>`;
}

const STATUS_LABELS = {
  idle: "Не запущен", starting: "Подключение…", live: "В эфире",
  stopping: "Остановка…", error: "Ошибка",
};

export function StreamTab() {
  const [blocks, setBlocks] = useState([{ files: [], count: 1 }]);
  const [rtmpUrl, setRtmpUrl] = useState("");
  const [streamKey, setStreamKey] = useState("");
  const [width, setWidth] = useState(1080);
  const [height, setHeight] = useState(1920);
  const [fps, setFps] = useState(30);
  const [videoBitrate, setVideoBitrate] = useState("4500k");
  const [state, setState] = useState(IDLE_STATE);
  const [uploadFrac, setUploadFrac] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/stream/status")
      .then(r => r.json())
      .then(j => {
        setState(j);
        if (j.status === "starting" || j.status === "live") { setBusy(true); connectWs(); }
      })
      .catch(() => {});
  }, []);

  const connectWs = () => {
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/stream/ws`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setState(j);
      if (j.status !== "starting" && j.status !== "live" && j.status !== "stopping") setBusy(false);
    };
  };

  const swap = () => { setWidth(height); setHeight(width); };

  const setBlockCount = n => setBlocks(prev => {
    n = Math.max(1, Math.floor(n) || 1);
    if (n === prev.length) return prev;
    if (n > prev.length) return [...prev, ...Array.from({ length: n - prev.length }, () => ({ files: [], count: 1 }))];
    return prev.slice(0, n);
  });

  const addBlock = () => setBlocks(prev => [...prev, { files: [], count: 1 }]);
  const removeBlock = i => setBlocks(prev => prev.length > 1 ? prev.filter((_, idx) => idx !== i) : prev);
  const setBlockFiles = (i, files) => setBlocks(prev => prev.map((b, idx) => idx === i ? { ...b, files } : b));
  const setBlockCountAt = (i, count) => setBlocks(prev => prev.map((b, idx) => idx === i ? { ...b, count: Math.max(1, Math.floor(count) || 1) } : b));

  const canStart = blocks.every(b => b.files.length > 0) && rtmpUrl.trim() && streamKey.trim() && !busy
    && state.status !== "starting" && state.status !== "live" && state.status !== "stopping";

  const startStream = async () => {
    if (!canStart) return;
    setBusy(true);
    setUploadFrac(0);
    setState({ ...IDLE_STATE, status: "starting", message: "Загрузка…" });

    const fd = new FormData();
    blocks.forEach(({ files }, i) => files.forEach(f => {
      fd.append("files", f);
      fd.append("blocks", String(i));
    }));
    blocks.forEach(({ count }) => fd.append("counts", String(count)));
    fd.append("rtmp_url", rtmpUrl.trim());
    fd.append("stream_key", streamKey.trim());
    fd.append("width", width);
    fd.append("height", height);
    fd.append("fps", fps);
    fd.append("video_bitrate", videoBitrate);

    const r = await uploadWithProgress("/api/stream/start", fd, setUploadFrac);
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      setState({ ...IDLE_STATE, status: "error", message: j.detail || "Ошибка запроса" });
      setBusy(false);
      return;
    }
    connectWs();
  };

  const stopStream = async () => {
    setBusy(true);
    await fetch("/api/stream/stop", { method: "POST" });
  };

  const live = state.status === "starting" || state.status === "live" || state.status === "stopping";
  const pct = combinedPct(uploadFrac, 0);

  return html`
    <h1 class="mb-6 text-lg font-semibold">Стрим</h1>

    <label class="mb-5 block text-sm">
      <span class="mb-1 block text-neutral-400">Количество блоков</span>
      <input type="number" min="1" value=${blocks.length} onInput=${e => setBlockCount(+e.target.value)} disabled=${live}
        class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
    </label>

    ${blocks.map(({ files, count }, i) => html`<${Block} key=${i} index=${i} files=${files} count=${count}
      onFiles=${f => setBlockFiles(i, f)} onRemove=${() => removeBlock(i)} removable=${blocks.length > 1 && !live}
      onCountChange=${c => setBlockCountAt(i, c)} />`)}

    <button type="button" onClick=${addBlock} disabled=${live}
      class="mb-5 w-full rounded-lg border border-dashed border-neutral-700 px-4 py-2 text-sm text-neutral-400 transition hover:border-neutral-500 hover:text-neutral-200 disabled:opacity-50">
      + Добавить блок
    </button>

    <div class="mb-5 grid grid-cols-2 gap-3">
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">RTMP URL</span>
        <input type="text" value=${rtmpUrl} onInput=${e => setRtmpUrl(e.target.value)} disabled=${live}
          placeholder="rtmp://a.rtmp.youtube.com/live2"
          class="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
      </label>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Stream key</span>
        <input type="text" value=${streamKey} onInput=${e => setStreamKey(e.target.value)} disabled=${live}
          class="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
      </label>
    </div>

    <div class="mb-5 flex items-end gap-3">
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Ширина</span>
        <input type="number" min="2" value=${width} onInput=${e => setWidth(+e.target.value)} disabled=${live}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
      </label>
      <button type="button" title="Поменять Ш и В местами" onClick=${swap} disabled=${live}
        class="mb-[1px] rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-neutral-400 transition hover:border-neutral-500 hover:text-neutral-200 disabled:opacity-50">⇄</button>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Высота</span>
        <input type="number" min="2" value=${height} onInput=${e => setHeight(+e.target.value)} disabled=${live}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
      </label>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">FPS</span>
        <input type="number" min="1" value=${fps} onInput=${e => setFps(+e.target.value)} disabled=${live}
          class="w-24 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
      </label>
      <label class="text-sm">
        <span class="mb-1 block text-neutral-400">Битрейт видео</span>
        <input type="text" value=${videoBitrate} onInput=${e => setVideoBitrate(e.target.value)} disabled=${live}
          class="w-28 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500 disabled:opacity-50" />
      </label>
    </div>

    ${!live && html`
      <button onClick=${startStream} disabled=${!canStart}
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
        Начать стрим
      </button>
    `}
    ${live && html`
      <button onClick=${stopStream} disabled=${state.status === "stopping"}
        class="w-full rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50">
        Остановить стрим
      </button>
    `}

    <div class="mt-6">
      <div class="mb-2 flex justify-between text-xs text-neutral-400">
        <span>${STATUS_LABELS[state.status] || state.status}${state.message ? " — " + state.message : ""}</span>
        ${state.status === "starting" && !state.pass_number ? html`<span>${pct}%</span>` : null}
      </div>
      ${state.status === "starting" && !state.pass_number && html`
        <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
          <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: pct + "%" }}></div>
        </div>
      `}
      ${(state.status === "live" || state.pass_number > 0) && html`
        <div class="text-sm text-neutral-400">
          Проход №${state.pass_number}${state.current_file ? html` · сейчас: <span class="text-neutral-200">${state.current_file}</span>` : null}
        </div>
      `}
    </div>
  `;
}
