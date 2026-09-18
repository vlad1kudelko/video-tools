import asyncio

from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import FileResponse

from . import s3_store
from .registry import MODULES
from .runner import NODE_RESULTS, RUNS, GraphRequest, clear_all_results, new_run, run_pipeline

router = APIRouter()


@router.get("/api/modules")
def list_modules():
    return [
        {
            "id": m.id,
            "label": m.label,
            "params_schema": m.params_model.model_json_schema(),
            "input_port": m.input_port.value if m.input_port else None,
            "block_input": m.block_input.value if m.block_input else None,
            "output_port": m.output_port.value,
            "description": m.description,
        }
        for m in MODULES.values()
    ]


@router.post("/api/pipeline/run")
async def start_run(graph: GraphRequest):
    if not graph.nodes:
        raise HTTPException(400, "empty graph")
    run = new_run()
    asyncio.create_task(run_pipeline(run, graph))
    return {"run_id": run.id}


@router.websocket("/api/pipeline/ws/{run_id}")
async def ws(run_id: str, sock: WebSocket):
    await sock.accept()
    run = RUNS.get(run_id)
    if not run:
        await sock.send_json({"status": "error", "nodes": []})
        return await sock.close()
    while True:
        await sock.send_json({
            "status": run.status,
            "nodes": [
                {
                    "node_id": n.node_id, "module_id": n.module_id,
                    "status": n.status, "message": n.message, "progress": round(n.progress, 3),
                }
                for n in run.nodes
            ],
        })
        if run.status != "processing":
            break
        await asyncio.sleep(0.25)
    await sock.close()


@router.post("/api/pipeline/clear")
def clear_files():
    clear_all_results()
    return {"ok": True}


@router.get("/api/pipeline/node/{node_id}/file")
def download_node_result(node_id: str):
    # No cleanup on download — the file stays cached until an explicit
    # clear or a fresh run recomputes it.
    path = NODE_RESULTS.get(node_id)
    if not path or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, filename=path.name)


@router.get("/api/pipeline/presets")
def list_presets():
    return s3_store.list_presets()


@router.get("/api/pipeline/presets/{name}")
def get_preset(name: str):
    data = s3_store.get_preset(name)
    if data is None:
        raise HTTPException(404)
    return data


@router.post("/api/pipeline/graphs")
def save_graph(graph: dict):
    graph_id = s3_store.save_graph(graph)
    return {"id": graph_id}


@router.get("/api/pipeline/graphs/{graph_id}")
def get_graph(graph_id: str):
    data = s3_store.get_graph(graph_id)
    if data is None:
        raise HTTPException(404)
    return data
