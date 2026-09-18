import { Handle, Position } from "@xyflow/react";
import {
  ParamField,
  fileToBase64,
  STATUS_LABELS,
  portHandleStyle,
  DeleteNodeButton,
  NodeStatusDot,
  NodeProgressBar,
} from "./nodeShared.jsx";

export default function CombinatorNode({ id, data, selected }) {
  const { manifest, params, blocks = [], status, statusLabel, progress } = data;
  const schemaProps = manifest?.params_schema?.properties || {};

  const onBlockFileInput = async (blockId, e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    data.onBlockInlineFileChange(id, blockId, base64, file.name);
  };

  return (
    <div
      className={`w-64 rounded-xl border bg-neutral-900 shadow-lg ${
        selected ? "border-indigo-500 ring-2 ring-indigo-500/40" : "border-neutral-700"
      }`}
    >
      <div className="flex items-center justify-between rounded-t-xl border-b border-neutral-800 bg-neutral-800/60 px-3 py-2 text-sm font-semibold text-neutral-100">
        <span>{manifest?.label || "Комбинатор"}</span>
        <div className="flex items-center gap-1.5">
          <NodeStatusDot status={status} onRunFromHere={() => data.onRunFromHere?.(id)} />
          <DeleteNodeButton onClick={() => data.onDeleteNode?.(id)} />
        </div>
      </div>

      <div className="space-y-3 p-3">
        {blocks.map((block, i) => (
          <div key={block.id} className="rounded-md border border-neutral-800 p-2">
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-medium text-neutral-300">Блок {i + 1}</span>
              <button
                type="button"
                onClick={() => data.onRemoveBlock(id, block.id)}
                disabled={blocks.length <= 1}
                className="text-xs text-neutral-500 hover:text-neutral-300 disabled:cursor-not-allowed disabled:opacity-30"
              >
                ✕
              </button>
            </div>

            <div className="relative mb-1.5">
              <Handle
                type="target"
                position={Position.Left}
                id={`block-${block.id}`}
                style={portHandleStyle(manifest?.block_input)}
              />
              {block.connected ? (
                <div className="rounded-md border border-dashed border-neutral-700 px-2 py-2 text-xs text-neutral-400">
                  ← подключено
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-neutral-700 px-2 py-2 text-xs">
                  <input
                    type="file"
                    onChange={(e) => onBlockFileInput(block.id, e)}
                    className="w-full text-xs text-neutral-400"
                  />
                  {block.inlineFileName && <div className="mt-1 truncate text-neutral-300">{block.inlineFileName}</div>}
                </div>
              )}
            </div>

            <label className="block text-xs">
              <span className="mb-0.5 block text-neutral-400">Количество</span>
              <input
                type="number"
                min={1}
                value={block.count}
                onFocus={() => data.onFieldFocus?.()}
                onChange={(e) => data.onBlockCountChange(id, block.id, Math.max(1, Math.floor(Number(e.target.value)) || 1))}
                className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-100 outline-none focus:border-indigo-500"
              />
            </label>
          </div>
        ))}

        <button
          type="button"
          onClick={() => data.onAddBlock(id)}
          className="w-full rounded-md border border-dashed border-neutral-700 px-2 py-1.5 text-xs text-neutral-400 transition hover:border-neutral-500 hover:text-neutral-200"
        >
          + Добавить блок
        </button>

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

      {status && (
        <>
          <NodeProgressBar status={status} progress={progress} />
          <div className="rounded-b-xl border-t border-neutral-800 px-3 py-1.5 text-xs text-neutral-400">
            {statusLabel || STATUS_LABELS[status] || status}
          </div>
        </>
      )}
    </div>
  );
}
