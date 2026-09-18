import asyncio
import base64
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from .manifest import PipelineInput
from .registry import MODULES

POLL_SECONDS = 0.25


@dataclass
class NodeStatus:
    node_id: str
    module_id: str
    status: str = "queued"  # queued | processing | done | error
    message: str = ""


@dataclass
class PipelineRun:
    id: str
    nodes: list[NodeStatus] = field(default_factory=list)
    status: str = "processing"  # processing | done | error
    result: Path | None = None  # last node's output — the whole run's deliverable


RUNS: dict[str, PipelineRun] = {}


class GraphNode(BaseModel):
    node_id: str
    module_id: str
    params: dict = {}
    input: dict | None = None  # {"kind": "inline"|"edge", ...} — see _resolve_input


class GraphRequest(BaseModel):
    nodes: list[GraphNode]


def new_run() -> PipelineRun:
    run = PipelineRun(id=uuid4().hex[:12])
    RUNS[run.id] = run
    return run


def _resolve_input(node: GraphNode, results: dict[str, Path]) -> PipelineInput | None:
    if not node.input:
        return None
    kind = node.input.get("kind")
    if kind == "inline":
        text = node.input.get("text")
        if text:
            return PipelineInput(name="input.txt", text=text)
        b64 = node.input.get("data_base64")
        if b64:
            return PipelineInput(name=node.input.get("name") or "input", data=base64.b64decode(b64))
        return None
    if kind == "edge":
        src_id = node.input.get("from")
        src_path = results.get(src_id)
        if src_path is None:
            raise RuntimeError(f"нет результата у узла {src_id}")
        return PipelineInput(name=src_path.name, data=src_path.read_bytes())
    return None


async def run_pipeline(run: PipelineRun, graph: GraphRequest) -> None:
    """Strictly sequential — no parallelism, no caching. One node at a time,
    in the order the frontend already topologically sorted before sending."""
    results: dict[str, Path] = {}
    completed_workdirs: list[Path] = []  # every node's own TMP/job.id, in order
    status_map = {n.node_id: NodeStatus(node_id=n.node_id, module_id=n.module_id) for n in graph.nodes}
    run.nodes = list(status_map.values())

    for node in graph.nodes:
        st = status_map[node.node_id]
        manifest = MODULES.get(node.module_id)
        if manifest is None:
            st.status, st.message = "error", f"неизвестный модуль {node.module_id}"
            run.status = "error"
            _cleanup_all(completed_workdirs)
            return
        try:
            params = manifest.params_model.model_validate(node.params)
            inp = _resolve_input(node, results)
            st.status = "processing"
            job = await manifest.start(inp, params)
            while job.status == "processing":
                st.message = job.message
                await asyncio.sleep(POLL_SECONDS)
            st.message = job.message
            if job.status != "done" or not job.result:
                st.status = "error"
                run.status = "error"
                _cleanup_all(completed_workdirs)
                return
            st.status = "done"
            results[node.node_id] = job.result
            run.result = job.result
            completed_workdirs.append(job.result.parent)  # every module's result lives at TMP/job.id/<file>
        except Exception as exc:  # noqa: BLE001
            st.status, st.message = "error", str(exc)
            run.status = "error"
            _cleanup_all(completed_workdirs)
            return
    run.status = "done"
    # Every intermediate node's workdir has already been consumed by the next
    # node (its bytes were read into memory) — only the final result, kept as
    # `run.result`, needs to survive until it's downloaded.
    for workdir in completed_workdirs[:-1]:
        shutil.rmtree(workdir, ignore_errors=True)


def _cleanup_all(workdirs: list[Path]) -> None:
    for workdir in workdirs:
        shutil.rmtree(workdir, ignore_errors=True)


def cleanup_run(run_id: str) -> None:
    run = RUNS.pop(run_id, None)
    if run and run.result:
        shutil.rmtree(run.result.parent, ignore_errors=True)
