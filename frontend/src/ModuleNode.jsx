import { Handle, Position } from "@xyflow/react";

function ParamField({ name, field, value, onChange }) {
  const label = field.title || name;
  const inputClass =
    "w-full rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-100 outline-none focus:border-indigo-500";

  if (field.enum) {
    return (
      <label className="block text-xs">
        <span className="mb-0.5 block text-neutral-400">{label}</span>
        <select value={value ?? field.default ?? ""} onChange={(e) => onChange(e.target.value)} className={inputClass}>
          {field.enum.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </label>
    );
  }
  if (field.type === "integer" || field.type === "number") {
    return (
      <label className="block text-xs">
        <span className="mb-0.5 block text-neutral-400">{label}</span>
        <input
          type="number"
          value={value ?? field.default ?? 0}
          onChange={(e) => onChange(Number(e.target.value))}
          className={inputClass}
        />
      </label>
    );
  }
  if (field.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-xs text-neutral-300">
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />
        <span>{label}</span>
      </label>
    );
  }
  return (
    <label className="block text-xs">
      <span className="mb-0.5 block text-neutral-400">{label}</span>
      <input type="text" value={value ?? field.default ?? ""} onChange={(e) => onChange(e.target.value)} className={inputClass} />
    </label>
  );
}

async function fileToBase64(file) {
  const buf = await file.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

const STATUS_LABELS = {
  queued: "в очереди",
  processing: "выполняется",
  done: "готово",
  error: "ошибка",
};

const STATUS_DOT = {
  queued: "bg-neutral-500",
  processing: "bg-amber-400 animate-pulse",
  done: "bg-emerald-500",
  error: "bg-red-500",
};

export default function ModuleNode({ id, data }) {
  const { manifest, params, connected, inlineText, inlineFileName, status, statusLabel } = data;
  const schemaProps = manifest?.params_schema?.properties || {};

  const onFileInput = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    data.onInlineFileChange(id, base64, file.name);
  };

  return (
    <div className="w-64 rounded-xl border border-neutral-700 bg-neutral-900 shadow-lg">
      <div className="flex items-center justify-between rounded-t-xl border-b border-neutral-800 bg-neutral-800/60 px-3 py-2 text-sm font-semibold text-neutral-100">
        <span>{manifest?.label || data.moduleId}</span>
        {status && <span className={`h-2 w-2 rounded-full ${STATUS_DOT[status] || "bg-neutral-500"}`} />}
      </div>

      <div className="space-y-3 p-3">
        {manifest?.input_port && (
          <div className="relative">
            <Handle type="target" position={Position.Left} id="in" />
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
            />
          ))}
        </div>
      </div>

      {manifest?.output_port && <Handle type="source" position={Position.Right} id="out" />}

      {status && (
        <div className="rounded-b-xl border-t border-neutral-800 px-3 py-1.5 text-xs text-neutral-400">
          {statusLabel || STATUS_LABELS[status] || status}
        </div>
      )}
    </div>
  );
}
