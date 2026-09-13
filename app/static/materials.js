const repoInput = $("#repo");
const scanBtn = $("#scan");
const tiles = $("#tiles");
const mPanel = $("#m-panel");
const mStatus = $("#m-status");
const mCount = $("#m-count");
const mBar = $("#m-bar");
const mDownload = $("#m-download");

const PHASE_PCT = {
  "Проверка репозитория": 15,
  "Чтение README": 45,
  "Загрузка сайта": 75,
};

const renderTiles = items => {
  tiles.innerHTML = items.map(it => it.kind === "video"
    ? `<a href="${it.url}" target="_blank" rel="noopener" title="${it.url}"
         class="flex aspect-square items-center justify-center rounded-lg border border-neutral-700 bg-neutral-900 p-2 text-center text-xs text-neutral-400 hover:border-indigo-500">▶ видео</a>`
    : `<a href="${it.url}" target="_blank" rel="noopener" title="${it.url}"
         class="block aspect-square overflow-hidden rounded-lg border border-neutral-700 bg-neutral-900">
         <img src="${it.url}" loading="lazy" class="h-full w-full object-cover" onerror="this.closest('a').remove()" />
       </a>`
  ).join("");
};

scanBtn.addEventListener("click", async () => {
  const repoUrl = repoInput.value.trim();
  if (!repoUrl) return;
  scanBtn.disabled = true;
  mDownload.classList.add("hidden");
  tiles.innerHTML = "";
  mPanel.classList.remove("hidden");
  mStatus.textContent = "Запуск…";
  mCount.textContent = "";
  mBar.style.width = "5%";

  const fd = new FormData();
  fd.append("repo_url", repoUrl);
  const r = await fetch("/api/materials/scan", { method: "POST", body: fd });
  if (!r.ok) {
    mStatus.textContent = "Ошибка запроса";
    scanBtn.disabled = false;
    return;
  }
  watchMaterials((await r.json()).id);
});

const watchMaterials = id => {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/materials/ws/${id}`);
  ws.onmessage = ev => {
    const j = JSON.parse(ev.data);
    renderTiles(j.items);
    mCount.textContent = j.items.length ? `${j.items.length} найдено` : "";
    if (j.status === "scanning") {
      mStatus.textContent = j.message || "Сканирование…";
      mBar.style.width = (PHASE_PCT[j.message] ?? 10) + "%";
    } else if (j.status === "done") {
      mStatus.textContent = j.message || "Готово";
      mBar.style.width = "100%";
      mDownload.href = `/api/materials/${id}/download`;
      mDownload.classList.remove("hidden");
      scanBtn.disabled = false;
    } else {
      mStatus.textContent = "Ошибка: " + (j.message || "неизвестно");
      mBar.style.width = "0%";
      scanBtn.disabled = false;
    }
  };
};
