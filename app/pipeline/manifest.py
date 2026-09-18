from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Protocol

from pydantic import BaseModel

from .types import PortType


@dataclass
class PipelineInput:
    """What flows into a node's data input. `data` is always the raw bytes;
    `text` is additionally populated whenever those bytes decode as UTF-8
    (true for an inline-pasted links list, and for any upstream node whose
    own output happens to be text-shaped, e.g. "Материалы" feeding
    "Скачивание" over an edge) — a text-input module reads `.text`, a
    file/archive-input module reads `.data`; either can be present without
    the other only for a genuinely binary source."""

    name: str = ""
    text: str | None = None
    data: bytes | None = None


@dataclass
class BlockInput:
    """One block of a dynamic block-list input (only "Комбинатор" uses this
    today) — a PipelineInput plus its own repeat count."""

    input: PipelineInput
    count: int


class JobLike(Protocol):
    """Every module's existing Job dataclass already has this shape — the
    runner polls it exactly the way each module's own WS handler already
    does, no new status abstraction needed."""

    status: str  # "processing" | "done" | "error"
    message: str
    result: Path | None
    progress: float  # 0.0-1.0 — drives the node's progress bar on the canvas


@dataclass
class ModuleManifest:
    id: str
    label: str
    params_model: type[BaseModel]
    output_port: PortType
    # Kicks off the module's job and returns the live job object.
    start: Callable[..., Awaitable[JobLike]]
    # Exactly one of these is set. input_port: start(PipelineInput | None, params).
    # block_input: start(list[BlockInput], params) — dynamic blocks, "Комбинатор" only.
    input_port: PortType | None = None
    block_input: PortType | None = None
    # Shown in an info tooltip on the canvas — a single sentence, or a list
    # of short points when the module has several distinct behaviors worth
    # calling out separately.
    description: str | list[str] = ""
