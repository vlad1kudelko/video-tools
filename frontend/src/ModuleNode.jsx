import { Handle, Position } from "@xyflow/react";
import {
  ParamField,
  fileToBase64,
  portHandleStyle,
  DeleteNodeButton,
  NodeStatusDot,
  NodeStatusFooter,
} from "./nodeShared.jsx";

export default function ModuleNode({ id, data, selected }) {
  const { manifest, params, connected, inlineText, inlineFileName, status, statusLabel, progress } = data;
  const schemaProps = manifest?.params_schema?.properties || {};

  const onFileInput = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    data.onInlineFileChange(id, base64, file.name);
  };

  return (
    <div
      className={`w-64 rounded-xl border bg-neutral-900 shadow-lg ${
        selected ? "border-indigo-500 ring-2 ring-indigo-500/40" : "border-neutral-700"
      }`}
    >
      <div className="flex items-center justify-between rounded-t-xl border-b border-neutral-800 bg-neutral-800/60 px-3 py-2 text-sm font-semibold text-neutral-100">
        <span>{manifest?.label || data.moduleId}</span>
        <div className="flex items-center gap-1.5">
          <NodeStatusDot status={status} onRunFromHere={() => data.onRunFromHere?.(id)} />
          <DeleteNodeButton onClick={() => data.onDeleteNode?.(id)} />
        </div>
      </div>

      <div className="space-y-3 p-3">
        {manifest?.input_port && (
          <div className="relative">
            <Handle type="target" position={Position.Left} id="in" style={portHandleStyle(manifest.input_port)} />
            {connected ? (
              <div className="rounded-md border border-dashed border-neutral-700 px-2 py-2 text-xs text-neutral-400">
                ← подключено
              </div>
            ) : manifest.input_port === "text_file" ? (
              <textarea
                placeholder="Ссылки, по одной на строку…"
                rows={3}
                value={inlineText || ""}
                onChange={(e) => data.onInlineTextChange(id, e.target.value)}
                className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-xs text-neutral-100 outline-none focus:border-indigo-500"
              />
            ) : (
              <div className="rounded-md border border-dashed border-neutral-700 px-2 py-2 text-xs">
                <input type="file" onChange={onFileInput} className="w-full text-xs text-neutral-400" />
                {inlineFileName && <div className="mt-1 truncate text-neutral-300">{inlineFileName}</div>}
              </div>
            )}
          </div>
        )}

        <div className="space-y-2">
          {Object.entries(schemaProps).map(([key, field]) => (
            <ParamField
              key={key}
              name={key}
              field={field}
              value={params?.[key]}
              onChange={(v) => data.onParamChange(id, key, v)}
              onFocus={() => data.onFieldFocus?.()}
            />
          ))}
        </div>
      </div>

      {manifest?.output_port && (
        <Handle type="source" position={Position.Right} id="out" style={portHandleStyle(manifest.output_port)} />
      )}

      <NodeStatusFooter nodeId={id} status={status} statusLabel={statusLabel} progress={progress} />
    </div>
  );
}
