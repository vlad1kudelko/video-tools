export async function listModules() {
  const r = await fetch("/api/modules");
  return r.json();
}

export async function listPresets() {
  const r = await fetch("/api/pipeline/presets");
  return r.json();
}

export async function loadPreset(name) {
  const r = await fetch(`/api/pipeline/presets/${name}`);
  return r.json();
}

export async function runPipeline(graph) {
  const r = await fetch("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTP ${r.status}`);
  }
  return r.json();
}

export async function clearAllFiles() {
  const r = await fetch("/api/pipeline/clear", { method: "POST" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export function subscribeRun(runId, onUpdate) {
  const ws = new WebSocket(
    `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/pipeline/ws/${runId}`
  );
  ws.onmessage = (ev) => onUpdate(JSON.parse(ev.data));
  return ws;
}
