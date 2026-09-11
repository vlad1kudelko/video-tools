const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const drop = $("#drop"), input = $("#file"), list = $("#list");
let files = [], mode = "blur", gravity = "center";

const TITLES = { blur: "Переформатирование под соотношение", crop: "Обрезка по cover" };

const applyMode = m => {
  mode = m;
  $("#title").textContent = TITLES[m];
  $("#gravity").classList.toggle("hidden", m !== "crop");
  $$(".mode").forEach(b => {
    const on = b.dataset.mode === m;
    b.className = "mode rounded-lg px-3 py-2 text-left text-sm font-medium transition " +
      (on ? "bg-indigo-600/20 text-indigo-300 ring-1 ring-inset ring-indigo-500/40"
          : "text-neutral-400 hover:bg-neutral-900");
  });
};

const applyGravity = g => {
  gravity = g;
  $$(".g").forEach(b => {
    const on = b.dataset.g === g;
    b.className = "g flex h-11 items-center justify-center rounded-lg border text-base transition " +
      (on ? "border-indigo-500 bg-indigo-600/20 text-indigo-300"
          : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-500");
  });
};

$("#swap").addEventListener("click", () => {
  [$("#w").value, $("#h").value] = [$("#h").value, $("#w").value];
});

$$(".mode").forEach(b => b.addEventListener("click", () => applyMode(b.dataset.mode)));
$$(".g").forEach(b => b.addEventListener("click", () => applyGravity(b.dataset.g)));
applyMode("blur");
applyGravity("center");

const render = () => {
  $("#go").disabled = !files.length;
  list.innerHTML = files.map(f => `<li class="truncate">• ${f.name}</li>`).join("");
};
const hl = on => drop.classList.toggle("border-indigo-500", on) || drop.classList.toggle("bg-neutral-900", on);

["dragenter", "dragover"].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); hl(true); }));
["dragleave", "drop"].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); hl(false); }));
drop.addEventListener("drop", ev => { files = [...ev.dataTransfer.files]; render(); });
drop.addEventListener("click", () => input.click());
input.addEventListener("change", () => { files = [...input.files]; render(); });

const setStatus = (text, pct) => {
  $("#panel").classList.remove("hidden");
  $("#status").textContent = text;
  $("#pct").textContent = pct == null ? "" : pct + "%";
  $("#bar").style.width = (pct ?? 0) + "%";
};

$("#go").addEventListener("click", async () => {
  const fd = new FormData();
  fd.append("width", $("#w").value);
  fd.append("height", $("#h").value);
  fd.append("mode", mode);
  fd.append("gravity", gravity);
  files.forEach(f => fd.append("files", f));
  $("#go").disabled = true;
  setStatus("Загрузка файлов…", null);
  const r = await fetch("/api/jobs", { method: "POST", body: fd });
  if (!r.ok) { setStatus("Ошибка запроса", 0); $("#go").disabled = false; return; }
  watch((await r.json()).id);
});

const watch = id => {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws/${id}`);
  ws.onmessage = ev => {
    const j = JSON.parse(ev.data);
    if (j.status === "processing") {
      setStatus(`Обработка ${Math.min(j.done + 1, j.total)} / ${j.total}`,
                Math.round(((j.done + j.progress) / j.total) * 100));
    } else if (j.status === "done") {
      setStatus("Готово — загрузка началась", 100);
      const a = document.createElement("a");
      a.href = `/api/jobs/${id}/download`;
      document.body.appendChild(a); a.click(); a.remove();
      $("#go").disabled = false;
    } else {
      setStatus("Ошибка: " + (j.message || "неизвестно"), 0);
      $("#go").disabled = false;
    }
  };
};
