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

export function InfoIcon({ description }) {
  if (!description) return null;
  const items = Array.isArray(description) ? description : null;
  return (
    <span className="group/info relative inline-flex shrink-0">
      <span className="flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-neutral-600 text-[10px] font-semibold leading-none text-neutral-500 transition-colors hover:border-neutral-400 hover:text-neutral-300">
        i
      </span>
      <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 hidden w-60 -translate-y-1/2 rounded-lg border border-neutral-700 bg-neutral-900 p-2.5 text-xs font-normal leading-snug text-neutral-300 shadow-xl group-hover/info:block">
        {items ? (
          <ul className="list-disc space-y-1 pl-3.5">
            {items.map((it, i) => (
              <li key={i}>{it}</li>
            ))}
          </ul>
        ) : (
          description
        )}
      </span>
    </span>
  );
}

export function CrossIcon({ size = 11 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" fill="none">
      <path d="M1.5 1.5L8.5 8.5M8.5 1.5L1.5 8.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function PlayIcon({ size = 10 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" fill="currentColor">
      <path d="M2 1.2L8.5 5L2 8.8V1.2Z" />
    </svg>
  );
}

// Doubles as a "run from this node onward" button.
const STATUS_COLORS = {
  idle: { base: "bg-neutral-400", hover: "hover:bg-neutral-600", icon: "text-neutral-950" },
  queued: { base: "bg-neutral-400", hover: "hover:bg-neutral-600", icon: "text-neutral-950" },
  processing: { base: "bg-amber-400 animate-pulse", hover: "hover:bg-amber-600", icon: "text-amber-950" },
  done: { base: "bg-emerald-400", hover: "hover:bg-emerald-600", icon: "text-emerald-950" },
  error: { base: "bg-red-400", hover: "hover:bg-red-600", icon: "text-red-950" },
};

export function NodeStatusDot({ status, onRunFromHere }) {
  const c = STATUS_COLORS[status] || STATUS_COLORS.idle;
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onRunFromHere?.();
      }}
      title="Запустить с этой ноды"
      className={`group flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-colors ${c.base} ${c.hover}`}
    >
      <span className={`flex items-center justify-center opacity-0 transition-opacity group-hover:opacity-100 ${c.icon}`}>
        <PlayIcon />
      </span>
    </button>
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
      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-neutral-400 text-neutral-950 transition-colors hover:bg-red-600 hover:text-red-950"
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

export function NodeProgressBar({ status, progress }) {
  if (status !== "processing" && status !== "done") return null;
  const pct = Math.round((progress || 0) * 100);
  return (
    <div className="h-1.5 w-full overflow-hidden bg-neutral-800">
      <div className="h-full bg-indigo-500 transition-all duration-300" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function NodeStatusFooter({ nodeId, status, statusLabel, progress }) {
  if (!status) return null;
  return (
    <>
      <NodeProgressBar status={status} progress={progress} />
      <div className="flex items-center justify-between gap-2 rounded-b-xl border-t border-neutral-800 px-3 py-1.5 text-xs text-neutral-400">
        <span className="truncate">{statusLabel || STATUS_LABELS[status] || status}</span>
        {status === "done" && (
          <a
            href={`/api/pipeline/node/${nodeId}/file`}
            onClick={(e) => e.stopPropagation()}
            title="Скачать результат этой ноды"
            className="shrink-0 rounded-md border border-emerald-600/50 bg-emerald-600/10 px-2 py-0.5 text-emerald-300 transition hover:bg-emerald-600/20"
          >
            ⬇ Скачать
          </a>
        )}
      </div>
    </>
  );
}

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
