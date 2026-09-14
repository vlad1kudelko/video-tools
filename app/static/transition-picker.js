const { h } = preact;
const { useState } = preactHooks;
const html = htm.bind(h);

export const TRANSITIONS = [
  { id: "none", label: "Без перехода", preview: null },
  { id: "fade", label: "Плавное перетекание" },
  { id: "wipeleft", label: "Шторка влево" },
  { id: "wiperight", label: "Шторка вправо" },
  { id: "wipeup", label: "Шторка вверх" },
  { id: "wipedown", label: "Шторка вниз" },
  { id: "slideleft", label: "Сдвиг влево" },
  { id: "slideright", label: "Сдвиг вправо" },
  { id: "slideup", label: "Сдвиг вверх" },
  { id: "slidedown", label: "Сдвиг вниз" },
  { id: "circlecrop", label: "Круг (обрезка)" },
  { id: "rectcrop", label: "Прямоугольник (обрезка)" },
  { id: "distance", label: "Дистанция" },
  { id: "fadeblack", label: "Через чёрный" },
  { id: "fadewhite", label: "Через белый" },
  { id: "radial", label: "Радиальный" },
  { id: "smoothleft", label: "Плавно влево" },
  { id: "smoothright", label: "Плавно вправо" },
  { id: "smoothup", label: "Плавно вверх" },
  { id: "smoothdown", label: "Плавно вниз" },
  { id: "circleopen", label: "Круг (открытие)" },
  { id: "circleclose", label: "Круг (закрытие)" },
  { id: "vertopen", label: "Открытие по вертикали" },
  { id: "vertclose", label: "Закрытие по вертикали" },
  { id: "horzopen", label: "Открытие по горизонтали" },
  { id: "horzclose", label: "Закрытие по горизонтали" },
  { id: "dissolve", label: "Растворение" },
  { id: "diagtl", label: "Диагональ ↖" },
  { id: "diagtr", label: "Диагональ ↗" },
  { id: "diagbl", label: "Диагональ ↙" },
  { id: "diagbr", label: "Диагональ ↘" },
  { id: "hlslice", label: "Полосы слева" },
  { id: "hrslice", label: "Полосы справа" },
  { id: "vuslice", label: "Полосы снизу" },
  { id: "vdslice", label: "Полосы сверху" },
  { id: "fadegrays", label: "Через чёрно-белое" },
  { id: "wipetl", label: "Шторка из угла ↖" },
  { id: "wipetr", label: "Шторка из угла ↗" },
  { id: "wipebl", label: "Шторка из угла ↙" },
  { id: "wipebr", label: "Шторка из угла ↘" },
  { id: "squeezeh", label: "Сжатие по горизонтали" },
  { id: "squeezev", label: "Сжатие по вертикали" },
].map(t => ({ ...t, preview: t.preview === null ? null : `${t.id}.gif` }));

function TransitionTile({ item, selected, onSelect }) {
  return html`
    <button type="button" onClick=${onSelect}
      class=${"flex flex-col items-stretch overflow-hidden rounded-lg border text-center transition " +
        (selected ? "border-indigo-500 ring-1 ring-indigo-500" : "border-neutral-700 hover:border-neutral-500")}>
      ${item.preview
        ? html`<img src=${`/previews/${item.preview}`} class="aspect-video w-full shrink-0 bg-neutral-900 object-cover" />`
        : html`<div class="flex aspect-video w-full shrink-0 items-center justify-center bg-neutral-900 text-lg text-neutral-500">✂</div>`}
      <div class="px-1 py-1 text-[11px] text-neutral-300">${item.label}</div>
    </button>`;
}

export function TransitionPicker({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const current = TRANSITIONS.find(t => t.id === value);

  return html`
    <div class="mt-5">
      <span class="mb-2 block text-sm text-neutral-400">Переход</span>
      <button type="button" onClick=${() => setOpen(o => !o)}
        class="flex w-full items-center justify-between rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-300 transition hover:border-neutral-500">
        <span>${current ? current.label : value}</span>
        <span class="text-neutral-500">${open ? "▲" : "▼"}</span>
      </button>
      ${open && html`
        <div class="mt-2 grid grid-cols-4 gap-2 sm:grid-cols-8">
          ${TRANSITIONS.map(t => html`<${TransitionTile} key=${t.id} item=${t} selected=${value === t.id}
            onSelect=${() => { onChange(t.id); setOpen(false); }} />`)}
        </div>
      `}
    </div>`;
}
