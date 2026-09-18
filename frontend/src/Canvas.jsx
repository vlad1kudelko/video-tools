import { useCallback, useEffect, useMemo, useState } from "react";
import { ReactFlow, Background, Controls, addEdge, useEdgesState, useNodesState } from "@xyflow/react";
import ModuleNode from "./ModuleNode.jsx";
import { listModules, listPresets, loadPreset, runPipeline, subscribeRun } from "./api.js";

const nodeTypes = { module: ModuleNode };

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

export default function Canvas() {
  const [modules, setModules] = useState({});
  const [presets, setPresets] = useState([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChangeRaw] = useEdgesState([]);
  const [runError, setRunError] = useState("");
  const [runId, setRunId] = useState(null);
  const [runDone, setRunDone] = useState(false);

  useEffect(() => {
    listModules().then((list) => {
      const byId = {};
      list.forEach((m) => {
        byId[m.id] = m;
      });
      setModules(byId);
    });
    listPresets().then(setPresets).catch(() => setPresets([]));
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

  const onInlineTextChange = useCallback((id, text) => updateNodeData(id, { inlineText: text }), [updateNodeData]);
  const onInlineFileChange = useCallback(
    (id, base64, name) => updateNodeData(id, { inlineFileBase64: base64, inlineFileName: name }),
    [updateNodeData]
  );

  const widgetHandlers = useMemo(
    () => ({ onParamChange, onInlineTextChange, onInlineFileChange }),
    [onParamChange, onInlineTextChange, onInlineFileChange]
  );

  // Connecting an edge disables the node's own inline widget; disconnecting
  // resets it to empty — it never held a value of its own while the edge
  // was supplying one, so there's nothing to restore.
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({ ...n, data: { ...n.data, connected: edges.some((e) => e.target === n.id) } }))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edges]);

  const onConnect = useCallback(
    (connection) => setEdges((eds) => addEdge({ ...connection, targetHandle: "in", sourceHandle: "out" }, eds)),
    [setEdges]
  );

  const onEdgesChange = useCallback(
    (changes) => {
      const removedIds = changes.filter((c) => c.type === "remove").map((c) => c.id);
      if (removedIds.length) {
        edges
          .filter((e) => removedIds.includes(e.id))
          .forEach((e) => updateNodeData(e.target, { inlineText: "", inlineFileBase64: null, inlineFileName: null }));
      }
      onEdgesChangeRaw(changes);
    },
    [edges, onEdgesChangeRaw, updateNodeData]
  );

  const isValidConnection = useCallback(
    (connection) => {
      const source = nodes.find((n) => n.id === connection.source);
      const target = nodes.find((n) => n.id === connection.target);
      if (!source || !target) return false;
      if (edges.some((e) => e.target === target.id)) return false; // one edge per input port
      return source.data.manifest?.output_port === target.data.manifest?.input_port;
    },
    [nodes, edges]
  );

  const addNode = (moduleId) => {
    const manifest = modules[moduleId];
    if (!manifest) return;
    const id = `${moduleId}-${Date.now()}`;
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: "module",
        position: { x: 80 + (nds.length % 4) * 260, y: 100 + Math.floor(nds.length / 4) * 220 },
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

  const applyPreset = async (name) => {
    const graph = await loadPreset(name);
    const newNodes = (graph.nodes || []).map((n, i) => {
      const manifest = modules[n.module_id];
      return {
        id: n.node_id,
        type: "module",
        position: n.position || { x: 120 + i * 260, y: 140 },
        data: {
          moduleId: n.module_id,
          manifest,
          params: { ...defaultParams(manifest?.params_schema), ...(n.params || {}) },
          inlineText: "",
          ...widgetHandlers,
        },
      };
    });
    setNodes(newNodes);
    setEdges([]);
  };

  const run = async () => {
    setRunError("");
    setRunDone(false);
    setRunId(null);
    const order = topoSort(nodes, edges);
    const graphNodes = order.map((id) => {
      const node = nodes.find((n) => n.id === id);
      const edge = edges.find((e) => e.target === id);
      let input = null;
      if (edge) {
        input = { kind: "edge", from: edge.source };
      } else if (node.data.inlineFileBase64) {
        input = { kind: "inline", data_base64: node.data.inlineFileBase64, name: node.data.inlineFileName };
      } else if (node.data.inlineText) {
        input = { kind: "inline", text: node.data.inlineText };
      }
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

  const chipClass =
    "rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm text-neutral-300 transition hover:border-neutral-500 hover:text-neutral-100";

  return (
    <div className="flex h-full flex-col bg-neutral-950 text-neutral-100">
      <div className="flex flex-wrap items-center gap-2 border-b border-neutral-800 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Добавить:</span>
        {Object.values(modules).map((m) => (
          <button key={m.id} onClick={() => addNode(m.id)} className={chipClass}>
            + {m.label}
          </button>
        ))}
        {presets.length > 0 && (
          <span className="ml-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Пресеты:</span>
        )}
        {presets.map((p) => (
          <button key={p} onClick={() => applyPreset(p)} className={chipClass}>
            {p}
          </button>
        ))}
        <button
          onClick={run}
          disabled={nodes.length === 0}
          className="ml-auto rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-neutral-800 disabled:text-neutral-500"
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
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
