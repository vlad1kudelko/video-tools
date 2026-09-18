from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Protocol

from pydantic import BaseModel

from .types import PortType


@dataclass
class PipelineInput:
    """What flows into a node's data input — either text (links.txt-shaped)
    or binary file/archive content, never both."""

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


@dataclass
class ModuleManifest:
    id: str
    label: str
    params_model: type[BaseModel]
    output_port: PortType
    # Kicks off the module's own existing job machinery (new_job() +
    # asyncio.create_task(run_*)) exactly like its routes.py does today, and
    # returns the live job object.
    start: Callable[..., Awaitable[JobLike]]
    # A node declares EITHER input_port (single input, most modules) OR
    # block_input (a dynamic list of same-typed blocks, "Комбинатор" only) —
    # never both. `start`'s signature follows: single-input modules take
    # (PipelineInput | None, params); block-input modules take
    # (list[BlockInput], params). The runner picks the calling convention by
    # checking which of these two is set.
    input_port: PortType | None = None
    block_input: PortType | None = None
