const { h } = preact;
const { useRef, useState } = preactHooks;
const html = htm.bind(h);

export function DropZone({ multiple = false, accept = "*", files, onFiles, hint }) {
  const [dragging, setDragging] = useState(false);
  const input = useRef(null);

  const pick = list => onFiles(multiple ? list : list.slice(0, 1));
  const countHint = multiple ? "можно несколько файлов" : "только один файл";

  return html`
    <div>
      <div
        onDragEnter=${e => { e.preventDefault(); setDragging(true); }}
        onDragOver=${e => { e.preventDefault(); setDragging(true); }}
        onDragLeave=${e => { e.preventDefault(); setDragging(false); }}
        onDrop=${e => { e.preventDefault(); setDragging(false); pick([...e.dataTransfer.files]); }}
        onClick=${() => input.current.click()}
        class=${"cursor-pointer rounded-xl border-2 border-dashed px-6 py-12 text-center transition " +
          (dragging ? "border-indigo-500 bg-neutral-900" : "border-neutral-700 bg-neutral-900/40")}
      >
        <p class="text-sm text-neutral-400">${hint || "Перетащите файл сюда или нажмите, чтобы выбрать"} (${countHint})</p>
        <ul class="mx-auto mt-3 max-w-sm space-y-1 text-left text-xs text-neutral-500">
          ${files.map(f => html`<li key=${f.name} class="truncate">• ${f.name}</li>`)}
        </ul>
      </div>
      <input ref=${input} type="file" accept=${accept} multiple=${multiple} class="hidden"
        onChange=${e => pick([...e.target.files])} />
    </div>`;
}
