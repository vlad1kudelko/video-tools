const { h } = preact;
const { useRef, useState } = preactHooks;
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
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState(null); // { text, pct }
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);

  const swap = () => { setW(ht); setHt(w); };

  const submit = async () => {
    setBusy(true);
    setStatus({ text: "Загрузка файлов…", pct: null });
    const fd = new FormData();
    fd.append("width", w);
    fd.append("height", ht);
    fd.append("mode", mode);
    fd.append("gravity", gravity);
    files.forEach(f => fd.append("files", f));
    const r = await fetch("/api/jobs", { method: "POST", body: fd });
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
        setStatus({ text: "Готово — загрузка началась", pct: 100 });
        const a = document.createElement("a");
        a.href = `/api/jobs/${id}/download`;
        document.body.appendChild(a); a.click(); a.remove();
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

    <div
      onDragEnter=${e => { e.preventDefault(); setDragging(true); }}
      onDragOver=${e => { e.preventDefault(); setDragging(true); }}
      onDragLeave=${e => { e.preventDefault(); setDragging(false); }}
      onDrop=${e => { e.preventDefault(); setDragging(false); setFiles([...e.dataTransfer.files]); }}
      onClick=${() => fileInput.current.click()}
      class=${"cursor-pointer rounded-xl border-2 border-dashed px-6 py-12 text-center transition " +
        (dragging ? "border-indigo-500 bg-neutral-900" : "border-neutral-700 bg-neutral-900/40")}
    >
      <p class="text-sm text-neutral-400">Перетащите видео сюда или нажмите, чтобы выбрать</p>
      <ul class="mx-auto mt-3 max-w-sm space-y-1 text-left text-xs text-neutral-500">
        ${files.map(f => html`<li key=${f.name} class="truncate">• ${f.name}</li>`)}
      </ul>
    </div>
    <input ref=${fileInput} type="file" accept="video/*" multiple class="hidden"
      onChange=${e => setFiles([...e.target.files])} />

    <button disabled=${!files.length || busy} onClick=${submit}
      class="mt-5 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Обработать
    </button>

    ${status && html`
      <div class="mt-6">
        <div class="mb-2 flex justify-between text-xs text-neutral-400">
          <span>${status.text}</span><span>${status.pct == null ? "" : status.pct + "%"}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
          <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: (status.pct ?? 0) + "%" }}></div>
        </div>
      </div>
    `}
  `;
}
