import { useEffect, useState } from "react";
import { Handle, Position } from "@xyflow/react";
import { listS3Files } from "./api.js";
import { portHandleStyle, DeleteNodeButton, InfoIcon, NodeStatusDot, NodeStatusFooter } from "./nodeShared.jsx";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export default function S3FileNode({ id, data, selected }) {
  const { manifest, params = {}, status, statusLabel, progress } = data;
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      setFiles(await listS3Files());
    } catch {
      setError("Не удалось получить список");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const setParam = (key, value) => data.onParamChange(id, key, value);
  const focus = () => data.onFieldFocus?.();

  return (
    <div
      className={`w-72 rounded-xl border bg-neutral-900 shadow-lg ${
        selected ? "border-indigo-500 ring-2 ring-indigo-500/40" : "border-neutral-700"
      }`}
    >
      <div className="flex items-center justify-between rounded-t-xl border-b border-neutral-800 bg-neutral-800/60 px-3 py-2 text-sm font-semibold text-neutral-100">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="truncate">{manifest?.label || "Файл из S3"}</span>
          <InfoIcon description={manifest?.description} />
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <NodeStatusDot status={status} onRunFromHere={() => data.onRunFromHere?.(id)} />
          <DeleteNodeButton onClick={() => data.onDeleteNode?.(id)} />
        </div>
      </div>

      <div className="space-y-2 p-3">
        <label className="block text-xs">
          <div className="mb-0.5 flex items-center justify-between">
            <span className="text-neutral-400">Файл</span>
            <button
              type="button"
              onClick={refresh}
              disabled={loading}
              title="Обновить список"
              className="text-neutral-500 transition hover:text-neutral-300 disabled:opacity-40"
            >
              ⟳
            </button>
          </div>
          <select
            value={params.key ?? ""}
            onFocus={focus}
            onChange={(e) => setParam("key", e.target.value)}
            className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          >
            <option value="">— выбрать —</option>
            {files.map((f) => (
              <option key={f.key} value={f.key}>
                {f.key} ({formatSize(f.size)})
              </option>
            ))}
          </select>
        </label>
        {error && <div className="text-xs text-red-400">{error}</div>}
        {!loading && !error && files.length === 0 && <div className="text-xs text-neutral-500">В бакете нет файлов</div>}
      </div>

      {manifest?.output_port && (
        <Handle type="source" position={Position.Right} id="out" style={portHandleStyle(manifest.output_port)} />
      )}

      <NodeStatusFooter nodeId={id} status={status} statusLabel={statusLabel} progress={progress} />
    </div>
  );
}
