import { useEffect, useState } from "react";
import { Handle, Position } from "@xyflow/react";
import { fileToBase64, portHandleStyle, DeleteNodeButton, InfoIcon, NodeStatusDot, NodeStatusFooter } from "./nodeShared.jsx";

const VIDEO_EXT = new Set([".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"]);

function isVideoName(name) {
  const dot = name.lastIndexOf(".");
  return dot >= 0 && VIDEO_EXT.has(name.slice(dot).toLowerCase());
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function CandidateTile({ candidate, order, onToggle, previewUrl }) {
  const selected = order != null;
  return (
    <button
      type="button"
      onClick={onToggle}
      title={`${candidate.name}${candidate.width ? ` — ${candidate.width}×${candidate.height}` : ""}, ${formatSize(candidate.size)}`}
      className={`relative aspect-square overflow-hidden rounded-md border bg-neutral-950 transition ${
        selected ? "border-indigo-500" : "border-neutral-700 opacity-50 hover:opacity-80"
      }`}
    >
      {isVideoName(candidate.name) ? (
        <video src={previewUrl} muted playsInline preload="metadata" className="h-full w-full object-cover" />
      ) : (
        <img src={previewUrl} loading="lazy" className="h-full w-full object-cover" />
      )}
      <span
        className={`absolute left-1 top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 text-[10px] font-semibold ${
          selected ? "border-indigo-500 bg-indigo-600 text-white" : "border-neutral-500 bg-neutral-900/80 text-neutral-400"
        }`}
      >
        {selected ? order : ""}
      </span>
    </button>
  );
}

export default function FilterNode({ id, data, selected }) {
  const { manifest, connected, inlineFileName, status, statusLabel, progress, candidates } = data;
  const [pick, setPick] = useState([]);

  // A fresh candidate batch (new run reaching "waiting") starts with a clean pick.
  useEffect(() => {
    setPick([]);
  }, [candidates]);

  const onFileInput = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    data.onInlineFileChange(id, base64, file.name);
  };

  const toggle = (candidateId) => {
    setPick((prev) => (prev.includes(candidateId) ? prev.filter((c) => c !== candidateId) : [...prev, candidateId]));
  };

  const orderOf = (candidateId) => {
    const i = pick.indexOf(candidateId);
    return i === -1 ? null : i + 1;
  };

  const submit = () => data.onSubmitSelection?.(id, pick);

  const isWaiting = status === "waiting";

  return (
    <div
      className={`w-72 rounded-xl border bg-neutral-900 shadow-lg ${
        selected ? "border-indigo-500 ring-2 ring-indigo-500/40" : "border-neutral-700"
      }`}
    >
      <div className="flex items-center justify-between rounded-t-xl border-b border-neutral-800 bg-neutral-800/60 px-3 py-2 text-sm font-semibold text-neutral-100">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="truncate">{manifest?.label || "Фильтрование"}</span>
          <InfoIcon description={manifest?.description} />
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <NodeStatusDot status={status} onRunFromHere={() => data.onRunFromHere?.(id)} />
          <DeleteNodeButton onClick={() => data.onDeleteNode?.(id)} />
        </div>
      </div>

      <div className="space-y-2 p-3">
        {!isWaiting && (
          <div className="relative">
            <Handle type="target" position={Position.Left} id="in" style={portHandleStyle(manifest?.input_port)} />
            {connected ? (
              <div className="rounded-md border border-dashed border-neutral-700 px-2 py-2 text-xs text-neutral-400">
                ← подключено
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-neutral-700 px-2 py-2 text-xs">
                <input type="file" onChange={onFileInput} className="w-full text-xs text-neutral-400" />
                {inlineFileName && <div className="mt-1 truncate text-neutral-300">{inlineFileName}</div>}
              </div>
            )}
          </div>
        )}

        {isWaiting && (
          <>
            <div className="text-xs text-neutral-400">
              Выбрано: {pick.length} из {candidates?.length ?? 0} — кликните по нужным, в порядке передачи
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {(candidates || []).map((c) => (
                <CandidateTile
                  key={c.id}
                  candidate={c}
                  order={orderOf(c.id)}
                  onToggle={() => toggle(c.id)}
                  previewUrl={`/api/pipeline/node/${id}/candidate/${c.id}`}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={submit}
              disabled={pick.length === 0}
              className="w-full rounded-md bg-indigo-600 px-2 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500"
            >
              Продолжить ({pick.length})
            </button>
          </>
        )}
      </div>

      {manifest?.output_port && (
        <Handle type="source" position={Position.Right} id="out" style={portHandleStyle(manifest.output_port)} />
      )}

      <NodeStatusFooter nodeId={id} status={status} statusLabel={statusLabel} progress={progress} />
    </div>
  );
}
