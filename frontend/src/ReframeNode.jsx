import { Handle, Position } from "@xyflow/react";
import {
  fileToBase64,
  portHandleStyle,
  DeleteNodeButton,
  InfoIcon,
  NodeStatusDot,
  NodeStatusFooter,
} from "./nodeShared.jsx";

const inputClass =
  "w-full rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-100 outline-none focus:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-40";

export default function ReframeNode({ id, data, selected }) {
  const { manifest, params = {}, connected, inlineFileName, status, statusLabel, progress } = data;
  const schemaProps = manifest?.params_schema?.properties || {};
  const modeOptions = schemaProps.mode?.enum || ["blur", "crop"];
  const gravityOptions = schemaProps.gravity?.enum || ["center", "top", "bottom", "left", "right"];
  const isCrop = params.mode === "crop";

  const setParam = (key, value) => data.onParamChange(id, key, value);
  const focus = () => data.onFieldFocus?.();
  const swap = () => {
    // One undo step, not two — the natural expectation for a single swap click.
    focus();
    setParam("width", params.height);
    setParam("height", params.width);
  };

  const onFileInput = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    data.onInlineFileChange(id, base64, file.name);
  };

  return (
    <div
      className={`w-72 rounded-xl border bg-neutral-900 shadow-lg ${
        selected ? "border-indigo-500 ring-2 ring-indigo-500/40" : "border-neutral-700"
      }`}
    >
      <div className="flex items-center justify-between rounded-t-xl border-b border-neutral-800 bg-neutral-800/60 px-3 py-2 text-sm font-semibold text-neutral-100">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="truncate">{manifest?.label || "Кадрирование"}</span>
          <InfoIcon description={manifest?.description} />
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <NodeStatusDot status={status} onRunFromHere={() => data.onRunFromHere?.(id)} />
          <DeleteNodeButton onClick={() => data.onDeleteNode?.(id)} />
        </div>
      </div>

      <div className="space-y-3 p-3">
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

        <div className="flex items-end gap-1.5">
          <label className="flex-1 text-xs">
            <span className="mb-0.5 block text-neutral-400">Width</span>
            <input
              type="number"
              value={params.width ?? 0}
              onFocus={focus}
              onChange={(e) => setParam("width", Number(e.target.value))}
              className={inputClass}
            />
          </label>
          <button
            type="button"
            title="Поменять Ш и В местами"
            onClick={swap}
            className="mb-[1px] shrink-0 rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1.5 text-neutral-400 transition hover:border-neutral-500 hover:text-neutral-200"
          >
            ⇄
          </button>
          <label className="flex-1 text-xs">
            <span className="mb-0.5 block text-neutral-400">Height</span>
            <input
              type="number"
              value={params.height ?? 0}
              onFocus={focus}
              onChange={(e) => setParam("height", Number(e.target.value))}
              className={inputClass}
            />
          </label>
        </div>

        <label className="block text-xs">
          <span className="mb-0.5 block text-neutral-400">Mode</span>
          <select value={params.mode ?? "blur"} onFocus={focus} onChange={(e) => setParam("mode", e.target.value)} className={inputClass}>
            {modeOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-xs">
          <span className="mb-0.5 block text-neutral-400">Gravity{!isCrop && " (только для crop)"}</span>
          <select
            value={params.gravity ?? "center"}
            disabled={!isCrop}
            onFocus={focus}
            onChange={(e) => setParam("gravity", e.target.value)}
            className={inputClass}
          >
            {gravityOptions.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-xs">
          <span className="mb-0.5 block text-neutral-400">Duration</span>
          <input
            type="number"
            min="0.1"
            step="0.1"
            value={params.duration ?? 3}
            onFocus={focus}
            onChange={(e) => setParam("duration", Number(e.target.value))}
            className={inputClass}
          />
        </label>
      </div>

      {manifest?.output_port && (
        <Handle type="source" position={Position.Right} id="out" style={portHandleStyle(manifest.output_port)} />
      )}

      <NodeStatusFooter nodeId={id} status={status} statusLabel={statusLabel} progress={progress} />
    </div>
  );
}
