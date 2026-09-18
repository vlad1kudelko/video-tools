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
    input_port: PortType | None
    # Kicks off the module's own existing job machinery (new_job() +
    # asyncio.create_task(run_*)) exactly like its routes.py does today, and
    # returns the live job object.
    start: Callable[[PipelineInput | None, BaseModel], Awaitable[JobLike]]
