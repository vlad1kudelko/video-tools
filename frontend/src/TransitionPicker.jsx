import { useState } from "react";
import { TRANSITIONS } from "./transitions.js";

export function TransitionPicker({ value, onChange, onFocus }) {
  const [open, setOpen] = useState(false);
  const current = TRANSITIONS.find((t) => t.id === value);

  return (
    <div className="text-xs">
      <span className="mb-0.5 block text-neutral-400">Переход</span>
      <button
        type="button"
        onClick={() => {
          onFocus?.();
          setOpen((o) => !o);
        }}
        className="flex w-full items-center justify-between rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1.5 text-sm text-neutral-100 transition hover:border-neutral-500"
      >
        <span className="truncate">{current ? current.label : value}</span>
        <span className="ml-1 shrink-0 text-neutral-500">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="mt-2 grid grid-cols-3 gap-1.5">
          {TRANSITIONS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                onChange(t.id);
                setOpen(false);
              }}
              className={`flex flex-col items-stretch overflow-hidden rounded-md border text-center transition ${
                value === t.id ? "border-indigo-500 ring-1 ring-indigo-500" : "border-neutral-700 hover:border-neutral-500"
              }`}
            >
              {t.preview ? (
                <img
                  src={`/previews/${t.preview}`}
                  className="aspect-video w-full shrink-0 bg-neutral-900 object-cover"
                />
              ) : (
                <div className="flex aspect-video w-full shrink-0 items-center justify-center bg-neutral-900 text-sm text-neutral-500">
                  ✂
                </div>
              )}
              <div className="px-1 py-0.5 text-[9px] leading-tight text-neutral-300">{t.label}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
