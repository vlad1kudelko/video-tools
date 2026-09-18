export async function listModules() {
  const r = await fetch("/api/modules");
  return r.json();
}

export async function saveGraph(graph) {
  const r = await fetch("/api/pipeline/graph", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function loadGraph() {
  const r = await fetch("/api/pipeline/graph");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function listS3Files() {
  const r = await fetch("/api/pipeline/s3-files");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
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
