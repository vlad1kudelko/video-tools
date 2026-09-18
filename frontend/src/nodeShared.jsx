export function ParamField({ name, field, value, onChange, onFocus }) {
  const label = field.title || name;
  const inputClass =
    "w-full rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-100 outline-none focus:border-indigo-500";

  if (field.enum) {
    return (
      <label className="block text-xs">
        <span className="mb-0.5 block text-neutral-400">{label}</span>
        <select
          value={value ?? field.default ?? ""}
          onFocus={onFocus}
          onChange={(e) => onChange(e.target.value)}
          className={inputClass}
        >
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
          onFocus={onFocus}
          onChange={(e) => onChange(Number(e.target.value))}
          className={inputClass}
        />
      </label>
    );
  }
  if (field.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-xs text-neutral-300">
        <input type="checkbox" checked={!!value} onFocus={onFocus} onChange={(e) => onChange(e.target.checked)} />
        <span>{label}</span>
      </label>
    );
  }
  return (
    <label className="block text-xs">
      <span className="mb-0.5 block text-neutral-400">{label}</span>
      <input
        type="text"
        value={value ?? field.default ?? ""}
        onFocus={onFocus}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      />
    </label>
  );
}

export function CrossIcon({ size = 9 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" fill="none">
      <path d="M1.5 1.5L8.5 8.5M8.5 1.5L1.5 8.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function DeleteNodeButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      title="Удалить ноду"
      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors hover:bg-red-600 hover:text-white"
    >
      <CrossIcon />
    </button>
  );
}

export async function fileToBase64(file) {
  const buf = await file.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

export const STATUS_LABELS = {
  queued: "в очереди",
  processing: "выполняется",
  done: "готово",
  error: "ошибка",
};

export const STATUS_DOT = {
  queued: "bg-neutral-500",
  processing: "bg-amber-400 animate-pulse",
  done: "bg-emerald-500",
  error: "bg-red-500",
};

export function NodeProgressBar({ status, progress }) {
  if (status !== "processing" && status !== "done") return null;
  const pct = Math.round((progress || 0) * 100);
  return (
    <div className="h-1.5 w-full overflow-hidden bg-neutral-800">
      <div className="h-full bg-indigo-500 transition-all duration-300" style={{ width: `${pct}%` }} />
    </div>
  );
}

// One color+shape per port type, applied to every connector dot (Handle) so
// compatibility is visible at a glance, not just enforced silently inside
// isValidConnection. Shape carries "single item vs. list" (circle vs.
// square), color carries the underlying data kind.
export const PORT_LEGEND = [
  { type: "text_file", color: "#f59e0b", shape: "circle", label: "текст" },
  { type: "video_file", color: "#38bdf8", shape: "circle", label: "видео" },
  { type: "video_file_list", color: "#a855f7", shape: "square", label: "список видео" },
];

const PORT_BY_TYPE = Object.fromEntries(PORT_LEGEND.map((p) => [p.type, p]));

export function portHandleStyle(portType) {
  const port = PORT_BY_TYPE[portType];
  const color = port?.color || "#6b7280";
  return {
    background: color,
    width: 12,
    height: 12,
    border: "2px solid #171717",
    borderRadius: port?.shape === "square" ? 3 : 9999,
  };
}
