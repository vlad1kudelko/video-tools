const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const PHASE_PCT = {
  "Проверка репозитория": 15,
  "Чтение README": 45,
  "Загрузка сайта": 75,
};
const SOURCE_LABELS = { readme: "Из README", site: "С сайта" };

function Tile({ item }) {
  if (item.kind === "video") {
    return html`
      <a href=${item.url} target="_blank" rel="noopener" title=${item.url}
        class="flex aspect-square items-center justify-center rounded-lg border border-neutral-700 bg-neutral-900 p-2 text-center text-xs text-neutral-400 hover:border-indigo-500">
        ▶ видео
      </a>`;
  }
  return html`
    <a href=${item.url} target="_blank" rel="noopener" title=${item.url}
      class="block aspect-square overflow-hidden rounded-lg border border-neutral-700 bg-neutral-900">
      <img src=${item.url} loading="lazy" class="h-full w-full object-cover"
        onError=${e => e.target.closest("a").remove()} />
    </a>`;
}

function groupBySource(items) {
  const groups = { readme: [], site: [] };
  for (const it of items) (groups[it.source] ??= []).push(it);
  return groups;
}

export function MaterialsTab() {
  const [repoUrl, setRepoUrl] = useState("");
  const [jobId, setJobId] = useState(null);
  const [state, setState] = useState(null); // { status, message, items }
  const [busy, setBusy] = useState(false);

  const scan = async () => {
    const url = repoUrl.trim();
    if (!url) return;
    setBusy(true);
    setJobId(null);
    setState({ status: "scanning", message: "Запуск…", items: [] });

    const fd = new FormData();
    fd.append("repo_url", url);
    const r = await fetch("/api/materials/scan", { method: "POST", body: fd });
    if (!r.ok) {
      setState({ status: "error", message: "Ошибка запроса", items: [] });
      setBusy(false);
      return;
    }
    const { id } = await r.json();
    setJobId(id);
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/materials/ws/${id}`);
    ws.onmessage = ev => {
      const j = JSON.parse(ev.data);
      setState(j);
      if (j.status !== "scanning") setBusy(false);
    };
  };

  const groups = state ? groupBySource(state.items) : { readme: [], site: [] };
  const pct = state?.status === "scanning" ? (PHASE_PCT[state.message] ?? 10) : state?.status === "done" ? 100 : 0;

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

    ${state && html`
      <div class="mt-6">
        <div class="mb-2 flex justify-between text-xs text-neutral-400">
          <span>${state.status === "error" ? "Ошибка: " + (state.message || "неизвестно") : (state.message || "—")}</span>
          <span>${state.items.length ? `${state.items.length} найдено` : ""}</span>
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
          ${groups[src].map(it => html`<${Tile} key=${it.url} item=${it} />`)}
        </div>
      </section>
    ` : null)}

    ${state?.status === "done" && html`
      <a href=${`/api/materials/${jobId}/download`}
        class="mt-6 block w-full rounded-xl bg-indigo-600 px-4 py-3 text-center text-sm font-semibold text-white transition hover:bg-indigo-500">
        Скачать links.txt
      </a>
    `}
  `;
}
