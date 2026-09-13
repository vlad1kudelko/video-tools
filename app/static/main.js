import { VideoTab } from "/video-static/video.js";
import { MaterialsTab } from "/materials-static/materials.js";

const { h, render } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

const TABS = [
  { id: "video", label: "Видео", Component: VideoTab },
  { id: "materials", label: "Подготовка материала", Component: MaterialsTab },
];

const navBtnClass = on =>
  "rounded-lg px-3 py-2 text-left text-sm font-medium transition " +
  (on ? "bg-indigo-600/20 text-indigo-300 ring-1 ring-inset ring-indigo-500/40" : "text-neutral-400 hover:bg-neutral-900");

function App() {
  const [tab, setTab] = useState("video");
  const active = TABS.find(t => t.id === tab);
  return html`
    <div class="flex min-h-screen flex-col md:flex-row">
      <aside class="shrink-0 border-b border-neutral-800 md:w-56 md:border-b-0 md:border-r">
        <div class="px-5 py-4 text-sm font-semibold tracking-wide text-neutral-400">VIDEO TOOLS</div>
        <nav class="flex gap-2 px-3 pb-3 md:flex-col md:pb-0">
          ${TABS.map(t => html`
            <button key=${t.id} class=${navBtnClass(t.id === tab)} onClick=${() => setTab(t.id)}>${t.label}</button>
          `)}
        </nav>
      </aside>
      <main class="mx-auto w-full max-w-4xl flex-1 px-5 py-8">
        <${active.Component} />
      </main>
    </div>
  `;
}

render(html`<${App} />`, document.getElementById("app"));
