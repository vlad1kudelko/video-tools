const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const PHASE_PCT = {
  "Проверка репозитория": 15,
  "Чтение README": 45,
  "Загрузка сайта": 75,
};
const SOURCE_LABELS = { readme: "Из README", site: "С сайта" };
const KIND_TITLES = { image: "images", gif: "gifs", video: "videos", other: "other" };

function mergeSelection(prev, items) {
  const next = new Map(prev);
  for (const it of items) {
    if (!next.has(it.url)) next.set(it.url, it.kind !== "other");
  }
  return next;
}

function groupBySource(items) {
  const groups = { readme: [], site: [] };
  for (const it of items) if (it.kind !== "other") groups[it.source].push(it);
  return groups;
}

function buildLinksText(items, selection) {
  const buckets = { image: [], gif: [], video: [], other: [] };
  for (const it of items) if (selection.get(it.url)) buckets[it.kind].push(it.url);
  const lines = [];
  for (const kind of ["image", "gif", "video", "other"]) {
    if (!buckets[kind].length) continue;
    lines.push(`# ${KIND_TITLES[kind]}`, ...buckets[kind], "");
  }
  return lines.join("\n").trim() + "\n";
}

function Tile({ item, selected, onToggle }) {
  const [broken, setBroken] = useState(false);
  const isPlaceholder = item.kind === "video" || broken;
  return html`
    <div class=${"relative aspect-square overflow-hidden rounded-lg border transition " +
      (selected ? "border-indigo-500" : "border-neutral-700 opacity-40")}>
      <a href=${item.url} target="_blank" rel="noopener" title=${item.url} class="block h-full w-full bg-neutral-900">
        ${isPlaceholder
          ? html`<div class="flex h-full w-full items-center justify-center p-2 text-center text-xs text-neutral-400">${item.kind === "video" ? "▶ видео" : "—"}</div>`
          : html`<img src=${item.url} loading="lazy" class="h-full w-full object-cover" onError=${() => setBroken(true)} />`}
      </a>
      <input type="checkbox" checked=${selected} onClick=${e => e.stopPropagation()} onChange=${() => onToggle(item.url)}
        class="absolute left-1 top-1 h-4 w-4 accent-indigo-500" />
    </div>`;
}

function OtherRow({ item, selected, onToggle }) {
  return html`
    <label class="flex items-center gap-2 rounded-lg border border-neutral-800 px-3 py-2 text-xs">
      <input type="checkbox" checked=${selected} onChange=${() => onToggle(item.url)} class="h-4 w-4 shrink-0 accent-indigo-500" />
      <a href=${item.url} target="_blank" rel="noopener" class="truncate text-neutral-400 hover:text-neutral-200">${item.url}</a>
      <span class="ml-auto shrink-0 text-neutral-600">${SOURCE_LABELS[item.source]}</span>
    </label>`;
}

export function MaterialsTab() {
  const [repoUrl, setRepoUrl] = useState("");
  const [items, setItems] = useState([]);
  const [selection, setSelection] = useState(new Map());
  const [meta, setMeta] = useState(null); // { status, message, filename }
  const [busy, setBusy] = useState(false);

  const toggle = url => setSelection(prev => {
    const next = new Map(prev);
    next.set(url, !next.get(url));
    return next;
  });

  const scan = async () => {
    const url = repoUrl.trim();
    if (!url) return;
    setBusy(true);
    setItems([]);
    setSelection(new Map());
    setMeta({ status: "scanning", message: "Запуск…", filename: "" });

    const fd = new FormData();
    fd.append("repo_url", url);
    const r = await fetch("/api/materials/scan", { method: "POST", body: fd });
    if (!r.ok) {
      setMeta({ status: "error", message: "Ошибка запроса", filename: "" });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/materials/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setItems(j.items);
      setSelection(prev => mergeSelection(prev, j.items));
      setMeta({ status: j.status, message: j.message, filename: j.filename });
      if (j.status !== "scanning") setBusy(false);
    };
  };

  const download = () => {
    const text = buildLinksText(items, selection);
    const blob = new Blob([text], { type: "text/plain" });
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objUrl;
    a.download = meta?.filename || "links.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objUrl);
  };

  const groups = groupBySource(items);
  const other = items.filter(it => it.kind === "other");
  const pct = meta?.status === "scanning" ? (PHASE_PCT[meta.message] ?? 10) : meta?.status === "done" ? 100 : 0;

  return html`
    <h1 class="mb-6 text-lg font-semibold">Подготовка материала</h1>

    <label class="mb-5 block text-sm">
      <span class="mb-1 block text-neutral-400">GitHub-репозиторий</span>
      <input type="text" value=${repoUrl} onInput=${e => setRepoUrl(e.target.value)}
        placeholder="https://github.com/owner/repo"
        class="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
    </label>

    <button onClick=${scan} disabled=${busy}
      class="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Сканировать
    </button>

    ${meta && html`
      <div class="mt-6">
        <div class="mb-2 flex justify-between text-xs text-neutral-400">
          <span>${meta.status === "error" ? "Ошибка: " + (meta.message || "неизвестно") : (meta.message || "—")}</span>
          <span>${items.length ? `${items.length} найдено` : ""}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
          <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: pct + "%" }}></div>
        </div>
      </div>
    `}

    ${["readme", "site"].map(src => groups[src].length ? html`
      <section key=${src} class="mt-6">
        <h2 class="mb-2 text-sm font-medium text-neutral-400">${SOURCE_LABELS[src]}</h2>
        <div class="grid grid-cols-3 gap-2 sm:grid-cols-4">
          ${groups[src].map(it => html`<${Tile} key=${it.url} item=${it} selected=${!!selection.get(it.url)} onToggle=${toggle} />`)}
        </div>
      </section>
    ` : null)}

    ${other.length ? html`
      <section class="mt-6">
        <h2 class="mb-2 text-sm font-medium text-neutral-400">Остальные ссылки (на всякий случай)</h2>
        <div class="space-y-1">
          ${other.map(it => html`<${OtherRow} key=${it.url} item=${it} selected=${!!selection.get(it.url)} onToggle=${toggle} />`)}
        </div>
      </section>
    ` : null}

    ${meta?.status === "done" && html`
      <button onClick=${download}
        class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-center text-sm font-semibold text-white transition hover:bg-indigo-500">
        Скачать ${meta.filename || "links.txt"}
      </button>
    `}
  `;
}
