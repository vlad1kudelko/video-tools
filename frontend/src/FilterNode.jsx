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
  "rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-100 outline-none focus:border-indigo-500";

const MODE_OPTIONS = ["выкл", "понизить в выдаче", "полностью исключить"];

export default function FilterNode({ id, data, selected }) {
  const { manifest, params = {}, connected, inlineFileName, status, statusLabel, progress } = data;
  const schemaProps = manifest?.params_schema?.properties || {};

  const setParam = (key, value) => data.onParamChange(id, key, value);
  const focus = () => data.onFieldFocus?.();

  const onFileInput = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    data.onInlineFileChange(id, base64, file.name);
  };

  // Mode select + its threshold number field share one row — reading a
  // switch and the value it gates as two separate stacked rows was confusing.
  const ModeRow = ({ modeKey, thresholdKey, thresholdDefault, unit }) => (
    <label className="block text-xs">
      <span className="mb-0.5 block text-neutral-400">
        {schemaProps[modeKey]?.title || modeKey}
        {unit && `, ${unit}`}
      </span>
      <div className="flex gap-1.5">
        <select
          value={params[modeKey] ?? "выкл"}
          onFocus={focus}
          onChange={(e) => setParam(modeKey, e.target.value)}
          className={`${inputClass} min-w-0 flex-1`}
        >
          {(schemaProps[modeKey]?.enum || MODE_OPTIONS).map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
        {thresholdKey && (
          <input
            type="number"
            title={schemaProps[thresholdKey]?.title}
            value={params[thresholdKey] ?? thresholdDefault}
            onFocus={focus}
            onChange={(e) => setParam(thresholdKey, Number(e.target.value))}
            className={`${inputClass} w-16 shrink-0`}
          />
        )}
      </div>
    </label>
  );

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

        <ModeRow modeKey="density_mode" thresholdKey="density_threshold_kb_per_mp" thresholdDefault={50} />
        <ModeRow modeKey="alpha_mode" />
        <ModeRow modeKey="square_mode" thresholdKey="square_tolerance_pct" thresholdDefault={15} unit="%" />
      </div>

      {manifest?.output_port && (
        <Handle type="source" position={Position.Right} id="out" style={portHandleStyle(manifest.output_port)} />
      )}

      <NodeStatusFooter nodeId={id} status={status} statusLabel={statusLabel} progress={progress} />
    </div>
  );
}
