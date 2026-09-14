const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const PHASE_PCT = {
  "Проверка репозитория": 15,
  "Чтение README": 45,
  "Загрузка сайта": 75,
};
const SOURCE_LABELS = { readme: "Из README", site: "С сайта" };

function groupBySource(items) {
  const groups = { readme: [], site: [] };
  for (const it of items) if (it.kind !== "other") groups[it.source].push(it);
  return groups;
}

function sortGroup(items, sizes) {
  return [...items].sort((a, b) => {
    const aAnimated = a.kind !== "image" ? 0 : 1;
    const bAnimated = b.kind !== "image" ? 0 : 1;
    if (aAnimated !== bAnimated) return aAnimated - bAnimated;
    if (aAnimated === 1) return (sizes.get(b.url) ?? -1) - (sizes.get(a.url) ?? -1); // biggest image first
    return 0; // gifs/video keep their found order
  });
}

function buildLinksText(selectedOrder) {
  return selectedOrder.join("\n") + "\n";
}

function RoundToggle({ checked, onToggle, posClass = "" }) {
  return html`
    <button type="button" onClick=${e => { e.preventDefault(); e.stopPropagation(); onToggle(); }}
      class=${posClass + " h-4 w-4 shrink-0 rounded-full border-2 transition " +
        (checked ? "border-indigo-500 bg-indigo-600" : "border-neutral-500 bg-neutral-900/80")}>
    </button>`;
}

function SelectMark({ selected, order, onToggle, posClass }) {
  return html`
    <button type="button" onClick=${e => { e.preventDefault(); e.stopPropagation(); onToggle(); }}
      class=${posClass + " flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 font-semibold transition " +
        (selected ? "border-indigo-500 bg-indigo-600 text-sm text-white" : "border-neutral-500 bg-neutral-900/80")}>
      ${selected ? order : ""}
    </button>`;
}

function Tile({ item, order, onToggle, onSize }) {
  const [broken, setBroken] = useState(false);
  const isPlaceholder = item.kind === "video" || broken;
  const selected = order != null;
  return html`
    <div class=${"relative aspect-square overflow-hidden rounded-lg border transition " +
      (selected ? "border-indigo-500" : "border-neutral-700 opacity-40")}>
      <a href=${item.url} target="_blank" rel="noopener" title=${item.url} class="block h-full w-full bg-neutral-900">
        ${isPlaceholder
          ? html`<div class="flex h-full w-full items-center justify-center p-2 text-center text-xs text-neutral-400">${item.kind === "video" ? "▶ видео" : "—"}</div>`
          : html`<img src=${item.url} loading="lazy" class="h-full w-full object-cover" onError=${() => setBroken(true)}
              onLoad=${e => onSize(item.url, e.target.naturalWidth * e.target.naturalHeight)} />`}
      </a>
      <${SelectMark} selected=${selected} order=${order} onToggle=${() => onToggle(item.url)} posClass="absolute left-1 top-1" />
    </div>`;
}

function OtherRow({ item, order, onToggle }) {
  const selected = order != null;
  return html`
    <div class="flex items-center gap-2 rounded-lg border border-neutral-800 px-3 py-2 text-xs">
      <${SelectMark} selected=${selected} order=${order} onToggle=${() => onToggle(item.url)} posClass="" />
      <a href=${item.url} target="_blank" rel="noopener" class="truncate text-neutral-400 hover:text-neutral-200">${item.url}</a>
      <span class="ml-auto shrink-0 text-neutral-600">${SOURCE_LABELS[item.source]}</span>
    </div>`;
}

function GroupHeader({ label, items, selectedOrder, onSelectAll }) {
  const allSelected = items.length > 0 && items.every(it => selectedOrder.includes(it.url));
  return html`
    <div class="mb-2 flex items-center justify-between">
      <h2 class="text-sm font-medium text-neutral-400">${label}</h2>
      <div class="flex items-center gap-2 text-xs text-neutral-500">
        Выбрать всё
        <${RoundToggle} checked=${allSelected} onToggle=${() => onSelectAll(items, !allSelected)} />
      </div>
    </div>`;
}

export function MaterialsTab() {
  const [repoUrl, setRepoUrl] = useState("");
  const [items, setItems] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState([]); // urls, in the order they were clicked
  const [sizes, setSizes] = useState(new Map()); // url -> naturalWidth * naturalHeight, filled in as thumbnails load
  const [meta, setMeta] = useState({ status: "idle", message: "—", filename: "" });
  const [busy, setBusy] = useState(false);

  const toggle = url => setSelectedOrder(prev =>
    prev.includes(url) ? prev.filter(u => u !== url) : [...prev, url]);

  const reportSize = (url, area) => setSizes(prev =>
    prev.get(url) === area ? prev : new Map(prev).set(url, area));

  const selectAll = (groupItems, value) => setSelectedOrder(prev => {
    const groupUrls = groupItems.map(it => it.url);
    return value
      ? [...prev, ...groupUrls.filter(u => !prev.includes(u))]
      : prev.filter(u => !groupUrls.includes(u));
  });

  const scan = async () => {
    const url = repoUrl.trim();
    if (!url) return;
    setBusy(true);
    setItems([]);
    setSelectedOrder([]);
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
      setMeta({ status: j.status, message: j.message, filename: j.filename });
      if (j.status !== "scanning") setBusy(false);
    };
  };

  const download = () => {
    const text = buildLinksText(selectedOrder);
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
  const orderOf = url => {
    const i = selectedOrder.indexOf(url);
    return i === -1 ? null : i + 1;
  };
  const pct = meta.status === "scanning" ? (PHASE_PCT[meta.message] ?? 10) : meta.status === "done" ? 100 : 0;

  return html`
    <h1 class="mb-6 text-lg font-semibold">Подготовка материала</h1>

    <label class="mb-5 block text-sm">
      <span class="mb-1 block text-neutral-400">GitHub-репозиторий</span>
      <input type="text" value=${repoUrl} onInput=${e => setRepoUrl(e.target.value)}
        placeholder="https://github.com/owner/repo"
        class="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 outline-none focus:border-indigo-500" />
    </label>

    <button onClick=${scan} disabled=${!repoUrl.trim() || busy}
      class="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Сканировать
    </button>

    <div class="mt-6">
      <div class="mb-2 flex justify-between text-xs text-neutral-400">
        <span>${meta.status === "error" ? "Ошибка: " + (meta.message || "неизвестно") : (meta.message || "—")}</span>
        <span>${items.length ? `${items.length} найдено` : ""}</span>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-neutral-800">
        <div class="h-full bg-indigo-500 transition-all duration-300" style=${{ width: pct + "%" }}></div>
      </div>
    </div>

    <div class="mt-4 text-sm text-neutral-400">Выбрано: <span class="font-semibold text-neutral-200">${selectedOrder.length}</span> из ${items.length}</div>

    ${["readme", "site"].map(src => groups[src].length ? html`
      <section key=${src} class="mt-6">
        <${GroupHeader} label=${SOURCE_LABELS[src]} items=${groups[src]} selectedOrder=${selectedOrder} onSelectAll=${selectAll} />
        <div class="grid grid-cols-3 gap-2 sm:grid-cols-4">
          ${sortGroup(groups[src], sizes).map(it => html`<${Tile} key=${it.url} item=${it} order=${orderOf(it.url)} onToggle=${toggle} onSize=${reportSize} />`)}
        </div>
      </section>
    ` : null)}

    ${other.length ? html`
      <section class="mt-6">
        <${GroupHeader} label="Остальные ссылки" items=${other} selectedOrder=${selectedOrder} onSelectAll=${selectAll} />
        <div class="space-y-1">
          ${other.map(it => html`<${OtherRow} key=${it.url} item=${it} order=${orderOf(it.url)} onToggle=${toggle} />`)}
        </div>
      </section>
    ` : null}

    <button onClick=${download} disabled=${meta.status !== "done"}
      class="mt-6 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500">
      Скачать результат
    </button>
  `;
}
