import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ReactFlow, Background, Controls, addEdge, useEdgesState, useNodesState } from "@xyflow/react";
import ModuleNode from "./ModuleNode.jsx";
import CombinatorNode from "./CombinatorNode.jsx";
import DeletableEdge from "./DeletableEdge.jsx";
import { listModules, runPipeline, subscribeRun } from "./api.js";
import { PORT_LEGEND } from "./nodeShared.jsx";

const nodeTypes = { module: ModuleNode, combinator: CombinatorNode };
const edgeTypes = { deletable: DeletableEdge };

function topoSort(nodes, edges) {
  const order = [];
  const visited = new Set();
  function visit(id) {
    if (visited.has(id)) return;
    visited.add(id);
    edges.filter((e) => e.target === id).forEach((e) => visit(e.source));
    order.push(id);
  }
  nodes.forEach((n) => visit(n.id));
  return order;
}

function defaultParams(schema) {
  const out = {};
  Object.entries(schema?.properties || {}).forEach(([k, f]) => {
    out[k] = f.default;
  });
  return out;
}

function newBlockId() {
  return `blk-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

// "block-<id>" target handles belong to a Combinator node's individual
// blocks; a plain "in" handle belongs to a regular single-input node.
function blockIdFromHandle(handle) {
  return handle && handle.startsWith("block-") ? handle.slice("block-".length) : null;
}

// Same 6 entries, same order and numbering as the old per-module sidebar
// (app/static/main.js) — modules without a pipeline manifest yet show up
// disabled instead of just vanishing, so the list stays a complete map of
// what the app can do, not only what's wired into the canvas so far.
const SIDEBAR_ITEMS = [
  { id: "materials", fallbackLabel: "Материалы" },
  { id: "download", fallbackLabel: "Скачивание медиа" },
  { id: "record", fallbackLabel: "Запись экрана" },
  { id: "reframe", fallbackLabel: "Кадрирование" },
  { id: "concat", fallbackLabel: "Склейка видео" },
  { id: "combinator", fallbackLabel: "Комбинатор" },
];

export default function Canvas() {
  const [modules, setModules] = useState({});
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChangeRaw] = useEdgesState([]);
  const [runError, setRunError] = useState("");
  const [runId, setRunId] = useState(null);
  const [runDone, setRunDone] = useState(false);

  // Undo/redo: a stack of {nodes, edges} snapshots. `commit()` is called
  // right before any state-changing action to record what to go back to —
  // node objects are always replaced (never mutated in place) by every
  // updater below, so a shallow snapshot of the arrays is enough.
  //
  // `commit` gets frozen into node `data` at node-creation time (block-add,
  // field-focus handlers live there) and node data is never wholesale
  // replaced afterward — so a version of `commit` that closes over `nodes`/
  // `edges` directly would keep reading whatever those were AT CREATION
  // TIME, not the current state. Reading through a ref instead makes
  // `commit` referentially stable (created once) and always correct.
  const [past, setPast] = useState([]);
  const [future, setFuture] = useState([]);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);
  useEffect(() => {
    edgesRef.current = edges;
  }, [edges]);

  const commit = useCallback(() => {
    setPast((p) => [...p, { nodes: nodesRef.current, edges: edgesRef.current }]);
    setFuture([]);
  }, []);

  const undo = useCallback(() => {
    setPast((p) => {
      if (p.length === 0) return p;
      const prev = p[p.length - 1];
      setFuture((f) => [{ nodes: nodesRef.current, edges: edgesRef.current }, ...f]);
      setNodes(prev.nodes);
      setEdges(prev.edges);
      return p.slice(0, -1);
    });
  }, [setNodes, setEdges]);

  const redo = useCallback(() => {
    setFuture((f) => {
      if (f.length === 0) return f;
      const next = f[0];
      setPast((p) => [...p, { nodes: nodesRef.current, edges: edgesRef.current }]);
      setNodes(next.nodes);
      setEdges(next.edges);
      return f.slice(1);
    });
  }, [setNodes, setEdges]);

  // Ctrl+Z / Ctrl+Shift+Z (and Ctrl+Y) for the canvas — skipped while a text
  // field has focus so the browser's own native undo inside that field keeps
  // working instead of fighting with this one.
  useEffect(() => {
    const onKeyDown = (e) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod) return;
      const tag = document.activeElement?.tagName;
      const isEditable = tag === "INPUT" || tag === "TEXTAREA" || document.activeElement?.isContentEditable;
      if (isEditable) return;
      if (e.key === "z" || e.key === "Z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if (e.key === "y" || e.key === "Y") {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [undo, redo]);

  useEffect(() => {
    listModules().then((list) => {
      const byId = {};
      list.forEach((m) => {
        byId[m.id] = m;
      });
      setModules(byId);
    });
  }, []);

  const updateNodeData = useCallback(
    (id, patch) => {
      setNodes((nds) => nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n)));
    },
    [setNodes]
  );

  const onParamChange = useCallback(
    (id, key, value) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, params: { ...n.data.params, [key]: value } } } : n))
      );
    },
    [setNodes]
  );

  // One commit per edit session (focus → blur), not per keystroke — same
  // "from pickup to drop" idea applied to typing instead of dragging.
  const onFieldFocus = useCallback(() => commit(), [commit]);

  const onInlineTextChange = useCallback((id, text) => updateNodeData(id, { inlineText: text }), [updateNodeData]);
  const onInlineFileChange = useCallback(
    (id, base64, name) => updateNodeData(id, { inlineFileBase64: base64, inlineFileName: name }),
    [updateNodeData]
  );

  // Block-list handlers — only Combinator nodes use these.
  const updateBlocks = useCallback(
    (nodeId, fn) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, blocks: fn(n.data.blocks || []) } } : n))
      );
    },
    [setNodes]
  );

  const onAddBlock = useCallback(
    (nodeId) => {
      commit();
      updateBlocks(nodeId, (blocks) => [
        ...blocks,
        { id: newBlockId(), count: 1, inlineFileBase64: null, inlineFileName: null, connected: false },
      ]);
    },
    [commit, updateBlocks]
  );

  const onRemoveBlock = useCallback(
    (nodeId, blockId) => {
      commit();
      updateBlocks(nodeId, (blocks) => (blocks.length > 1 ? blocks.filter((b) => b.id !== blockId) : blocks));
    },
    [commit, updateBlocks]
  );

  const onBlockCountChange = useCallback(
    (nodeId, blockId, count) => {
      updateBlocks(nodeId, (blocks) => blocks.map((b) => (b.id === blockId ? { ...b, count } : b)));
    },
    [updateBlocks]
  );

  const onBlockInlineFileChange = useCallback(
    (nodeId, blockId, base64, name) => {
      updateBlocks(nodeId, (blocks) =>
        blocks.map((b) => (b.id === blockId ? { ...b, inlineFileBase64: base64, inlineFileName: name } : b))
      );
    },
    [updateBlocks]
  );

  const resetBlockInput = useCallback(
    (nodeId, blockId) => {
      updateBlocks(nodeId, (blocks) =>
        blocks.map((b) => (b.id === blockId ? { ...b, inlineFileBase64: null, inlineFileName: null } : b))
      );
    },
    [updateBlocks]
  );

  const widgetHandlers = useMemo(
    () => ({ onParamChange, onInlineTextChange, onInlineFileChange, onFieldFocus }),
    [onParamChange, onInlineTextChange, onInlineFileChange, onFieldFocus]
  );

  const combinatorHandlers = useMemo(
    () => ({ onParamChange, onFieldFocus, onAddBlock, onRemoveBlock, onBlockCountChange, onBlockInlineFileChange }),
    [onParamChange, onFieldFocus, onAddBlock, onRemoveBlock, onBlockCountChange, onBlockInlineFileChange]
  );

  // Connecting an edge disables the node's own inline widget; disconnecting
  // resets it to empty — it never held a value of its own while the edge
  // was supplying one, so there's nothing to restore. For a Combinator node
  // this applies per-block, keyed by which "block-<id>" handle the edge targets.
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.type === "combinator") {
          const blocks = (n.data.blocks || []).map((b) => ({
            ...b,
            connected: edges.some((e) => e.target === n.id && e.targetHandle === `block-${b.id}`),
          }));
          return { ...n, data: { ...n.data, blocks } };
        }
        return { ...n, data: { ...n.data, connected: edges.some((e) => e.target === n.id) } };
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edges]);

  // Shared by both ways an edge can go away: pressing Backspace/Delete on a
  // selected edge (native React Flow interaction, via onEdgesChange below)
  // and clicking the small × button rendered on the edge itself (DeletableEdge).
  const resetEdgeTarget = useCallback(
    (edge) => {
      const blockId = blockIdFromHandle(edge.targetHandle);
      if (blockId) resetBlockInput(edge.target, blockId);
      else updateNodeData(edge.target, { inlineText: "", inlineFileBase64: null, inlineFileName: null });
    },
    [resetBlockInput, updateNodeData]
  );

  const deleteEdge = useCallback(
    (edgeId) => {
      commit();
      const edge = edges.find((e) => e.id === edgeId);
      if (edge) resetEdgeTarget(edge);
      setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    },
    [commit, edges, setEdges, resetEdgeTarget]
  );

  const onConnect = useCallback(
    (connection) => {
      commit();
      setEdges((eds) => addEdge({ ...connection, type: "deletable", data: { onDelete: deleteEdge } }, eds));
    },
    [commit, setEdges, deleteEdge]
  );

  const onEdgesChange = useCallback(
    (changes) => {
      const removedIds = changes.filter((c) => c.type === "remove").map((c) => c.id);
      if (removedIds.length) {
        commit();
        edges.filter((e) => removedIds.includes(e.id)).forEach(resetEdgeTarget);
      }
      onEdgesChangeRaw(changes);
    },
    [commit, edges, onEdgesChangeRaw, resetEdgeTarget]
  );

  // A node drag is one undo step from pickup to drop — commit once at drag
  // start, not on every intermediate position update while the mouse moves.
  const onNodeDragStart = useCallback(() => commit(), [commit]);

  const onNodesChangeWrapped = useCallback(
    (changes) => {
      if (changes.some((c) => c.type === "remove")) commit();
      onNodesChange(changes);
    },
    [commit, onNodesChange]
  );

  const isValidConnection = useCallback(
    (connection) => {
      const source = nodes.find((n) => n.id === connection.source);
      const target = nodes.find((n) => n.id === connection.target);
      if (!source || !target) return false;
      // One edge per input port — for a Combinator block that means per
      // block handle, not per whole node (it can legitimately have several).
      if (edges.some((e) => e.target === target.id && e.targetHandle === connection.targetHandle)) return false;
      const targetPortType = target.type === "combinator" ? target.data.manifest?.block_input : target.data.manifest?.input_port;
      return source.data.manifest?.output_port === targetPortType;
    },
    [nodes, edges]
  );

  const addNode = (moduleId) => {
    const manifest = modules[moduleId];
    if (!manifest) return;
    commit();
    const id = `${moduleId}-${Date.now()}`;
    const position = { x: 80 + (nodes.length % 4) * 260, y: 100 + Math.floor(nodes.length / 4) * 220 };
    if (manifest.block_input) {
      setNodes((nds) => [
        ...nds,
        {
          id,
          type: "combinator",
          position,
          data: {
            moduleId,
            manifest,
            params: defaultParams(manifest.params_schema),
            blocks: [{ id: newBlockId(), count: 1, inlineFileBase64: null, inlineFileName: null, connected: false }],
            ...combinatorHandlers,
          },
        },
      ]);
      return;
    }
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: "module",
        position,
        data: {
          moduleId,
          manifest,
          params: defaultParams(manifest.params_schema),
          inlineText: "",
          ...widgetHandlers,
        },
      },
    ]);
  };

  // How one node's input resolves for the run request — an edge into the
  // given handle, else whatever's been supplied inline.
  const resolveInput = (targetHandle, widgetState) => {
    const edge = edges.find((e) => e.target === widgetState.nodeId && e.targetHandle === targetHandle);
    if (edge) return { kind: "edge", from: edge.source };
    if (widgetState.inlineFileBase64) {
      return { kind: "inline", data_base64: widgetState.inlineFileBase64, name: widgetState.inlineFileName };
    }
    if (widgetState.inlineText) return { kind: "inline", text: widgetState.inlineText };
    return null;
  };

  const run = async () => {
    setRunError("");
    setRunDone(false);
    setRunId(null);
    const order = topoSort(nodes, edges);
    const graphNodes = order.map((id) => {
      const node = nodes.find((n) => n.id === id);
      if (node.type === "combinator") {
        const blocks = (node.data.blocks || []).map((b) => ({
          input: resolveInput(`block-${b.id}`, { nodeId: id, inlineFileBase64: b.inlineFileBase64, inlineFileName: b.inlineFileName }),
          count: b.count,
        }));
        return { node_id: id, module_id: node.data.moduleId, params: node.data.params, blocks };
      }
      const input = resolveInput("in", {
        nodeId: id,
        inlineFileBase64: node.data.inlineFileBase64,
        inlineFileName: node.data.inlineFileName,
        inlineText: node.data.inlineText,
      });
      return { node_id: id, module_id: node.data.moduleId, params: node.data.params, input };
    });

    try {
      const { run_id } = await runPipeline({ nodes: graphNodes });
      setRunId(run_id);
      subscribeRun(run_id, (update) => {
        update.nodes.forEach((n) => updateNodeData(n.node_id, { status: n.status, statusLabel: n.message }));
        if (update.status === "done") setRunDone(true);
        if (update.status === "error") setRunError("Пайплайн завершился с ошибкой — см. статус ноды");
      });
    } catch (err) {
      setRunError(String(err.message || err));
    }
  };

  return (
    <div className="flex h-full flex-col bg-neutral-950 text-neutral-100 md:flex-row">
      <aside className="flex shrink-0 flex-col border-b border-neutral-800 md:h-full md:w-56 md:border-b-0 md:border-r">
        <div className="px-5 py-4 text-sm font-semibold tracking-wide text-neutral-400">VIDEO TOOLS</div>
        <nav className="flex gap-2 px-3 pb-3 md:flex-col md:pb-0">
          {SIDEBAR_ITEMS.map((item, i) => {
            const manifest = modules[item.id];
            return manifest ? (
              <button
                key={item.id}
                onClick={() => addNode(item.id)}
                className="rounded-lg px-3 py-2 text-left text-sm font-medium text-neutral-400 transition hover:bg-neutral-900"
              >
                {i + 1}. {manifest.label}
              </button>
            ) : (
              <button
                key={item.id}
                disabled
                title="Пока не подключено к пайплайну"
                className="cursor-not-allowed rounded-lg px-3 py-2 text-left text-sm font-medium text-neutral-700"
              >
                {i + 1}. {item.fallbackLabel}
              </button>
            );
          })}
        </nav>
        <div className="mt-auto border-t border-neutral-800 px-5 py-3">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-600">Типы портов</div>
          <div className="space-y-1">
            {PORT_LEGEND.map((p) => (
              <div key={p.type} className="flex items-center gap-2 text-xs text-neutral-400">
                <span
                  style={{
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    background: p.color,
                    borderRadius: p.shape === "square" ? 2 : 9999,
                  }}
                />
                <span>{p.label}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center gap-2 border-b border-neutral-800 px-4 py-3">
          <button
            onClick={undo}
            disabled={past.length === 0}
            title="Отменить (Ctrl+Z)"
            className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-300 transition hover:border-neutral-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ↺
          </button>
          <button
            onClick={redo}
            disabled={future.length === 0}
            title="Повторить (Ctrl+Shift+Z)"
            className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-300 transition hover:border-neutral-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ↻
          </button>
          <button
            onClick={run}
            disabled={nodes.length === 0}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500"
          >
            ▶ Запустить
          </button>
          {runDone && runId && (
            <a
              href={`/api/pipeline/${runId}/file`}
              onClick={() => {
                setRunDone(false);
                setRunId(null);
              }}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
            >
              ⬇ Скачать результат
            </a>
          )}
          {runError && <span className="text-sm text-red-400">{runError}</span>}
        </div>
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChangeWrapped}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStart={onNodeDragStart}
            isValidConnection={isValidConnection}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
