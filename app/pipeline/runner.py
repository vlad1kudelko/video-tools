import asyncio
import base64
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from .manifest import BlockInput, PipelineInput
from .registry import MODULES

POLL_SECONDS = 0.25


@dataclass
class NodeStatus:
    node_id: str
    module_id: str
    status: str = "queued"  # queued | processing | done | error
    message: str = ""
    progress: float = 0.0


@dataclass
class PipelineRun:
    id: str
    nodes: list[NodeStatus] = field(default_factory=list)
    status: str = "processing"  # processing | done | error


RUNS: dict[str, PipelineRun] = {}


class GraphNode(BaseModel):
    node_id: str
    module_id: str
    params: dict = {}
    input: dict | None = None  # {"kind": "inline"|"edge", ...} — see _resolve_input_dict
    blocks: list[dict] | None = None  # [{"input": {...same shape as `input`...}, "count": int}] — block-input modules only


class GraphRequest(BaseModel):
    nodes: list[GraphNode]
    start_from: str | None = None  # node_id to resume from — nodes before it reuse NODE_RESULTS instead of re-running


def new_run() -> PipelineRun:
    run = PipelineRun(id=uuid4().hex[:12])
    RUNS[run.id] = run
    return run


# Persists across separate runs of the same graph (keyed by node_id, which is
# stable across "Запустить"/"запустить с этой ноды" clicks as long as the
# node isn't deleted) — this is what makes resuming from a specific node
# possible without recomputing everything upstream of it.
NODE_RESULTS: dict[str, Path] = {}


def _clear_node_results(node_ids: list[str]) -> None:
    for node_id in node_ids:
        path = NODE_RESULTS.pop(node_id, None)
        if path:
            shutil.rmtree(path.parent, ignore_errors=True)


def clear_all_results() -> None:
    for path in NODE_RESULTS.values():
        shutil.rmtree(path.parent, ignore_errors=True)
    NODE_RESULTS.clear()
    RUNS.clear()


def _set_node_result(node_id: str, path: Path) -> None:
    """Recomputing a node (e.g. it's at/after start_from on a resumed run)
    overwrites its NODE_RESULTS entry — without this, the old workdir it
    pointed to would never get deleted and just leak on disk forever."""
    old = NODE_RESULTS.get(node_id)
    if old is not None and old.parent != path.parent:
        shutil.rmtree(old.parent, ignore_errors=True)
    NODE_RESULTS[node_id] = path


def _resolve_input_dict(input_dict: dict | None, results: dict[str, Path]) -> PipelineInput | None:
    """Shared by a node's single `input` and each block's own `input` in
    `blocks` — same {"kind": "inline"|"edge", ...} shape either way."""
    if not input_dict:
        return None
    kind = input_dict.get("kind")
    if kind == "inline":
        text = input_dict.get("text")
        if text:
            return PipelineInput(name="input.txt", text=text)
        b64 = input_dict.get("data_base64")
        if b64:
            return PipelineInput(name=input_dict.get("name") or "input", data=base64.b64decode(b64))
        return None
    if kind == "edge":
        src_id = input_dict.get("from")
        src_path = results.get(src_id)
        if src_path is None:
            raise RuntimeError(f"нет результата у узла {src_id}")
        data = src_path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        return PipelineInput(name=src_path.name, data=data, text=text)
    return None


async def run_pipeline(run: PipelineRun, graph: GraphRequest) -> None:
    """Strictly sequential — no parallelism. One node at a time, in the order
    the frontend already topologically sorted before sending.

    `graph.start_from`, when set, marks the node the user actually clicked
    "run" on — everything before it in the sent order (the frontend already
    scopes this to just its ancestors, see Canvas.jsx's subgraphNodeIds) is
    reused from NODE_RESULTS when a valid cache exists, and *computed* when
    it doesn't (an ancestor that was simply never run yet, e.g. because
    there's no separate "run everything" action anymore — clicking any node
    just works, filling in whatever upstream steps are still missing).
    `graph.start_from` itself, and everything the frontend included after it
    (its downstream chain), always execute for real, never from cache — that
    the clicked node re-runs is the whole point of clicking it. When unset,
    this is a full fresh run — the current graph's previous cached results
    are cleared first, exactly like starting over."""
    results: dict[str, Path] = {}
    status_map = {n.node_id: NodeStatus(node_id=n.node_id, module_id=n.module_id) for n in graph.nodes}
    run.nodes = list(status_map.values())

    if graph.start_from is None:
        _clear_node_results([n.node_id for n in graph.nodes])
        started = True
    else:
        started = False
        if not any(n.node_id == graph.start_from for n in graph.nodes):
            run.status = "error"
            return

    for node in graph.nodes:
        st = status_map[node.node_id]
        if not started:
            if node.node_id == graph.start_from:
                started = True
            else:
                cached = NODE_RESULTS.get(node.node_id)
                if cached is not None and cached.exists():
                    results[node.node_id] = cached
                    st.status, st.progress, st.message = "done", 1.0, "из кэша"
                    continue
                # No cache for this ancestor yet — compute it (and, from here
                # on, everything downstream too: a descendant's own cache, if
                # any, was built from this now-stale/missing input).
                started = True
        manifest = MODULES.get(node.module_id)
        if manifest is None:
            st.status, st.message = "error", f"неизвестный модуль {node.module_id}"
            run.status = "error"
            return
        try:
            params = manifest.params_model.model_validate(node.params)
            st.status = "processing"
            if manifest.block_input is not None:
                blocks = [
                    BlockInput(input=_resolve_input_dict(b.get("input"), results), count=max(1, int(b.get("count", 1))))
                    for b in (node.blocks or [])
                ]
                if not blocks:
                    raise RuntimeError("нужен хотя бы один блок")
                job = await manifest.start(blocks, params)
            else:
                inp = _resolve_input_dict(node.input, results)
                job = await manifest.start(inp, params)
            while job.status == "processing":
                st.message = job.message
                st.progress = getattr(job, "progress", 0.0)
                await asyncio.sleep(POLL_SECONDS)
            st.message = job.message
            if job.status != "done" or not job.result:
                st.status = "error"
                run.status = "error"
                return
            st.status = "done"
            st.progress = 1.0
            results[node.node_id] = job.result
            _set_node_result(node.node_id, job.result)
        except Exception as exc:  # noqa: BLE001
            st.status, st.message = "error", str(exc)
            run.status = "error"
            return
    run.status = "done"
    # No automatic cleanup here anymore — every node's result now persists
    # (in NODE_RESULTS) until an explicit clear_all_results() or a future
    # full (start_from=None) run of the same graph. RUNS entries are likewise
    # left alone so the result stays downloadable more than once — see
    # routes.py's download endpoint, which no longer cleans up after itself.
