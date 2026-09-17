from dataclasses import dataclass


@dataclass
class StreamState:
    status: str = "idle"  # idle | starting | live | stopping | error
    message: str = ""
    current_file: str = ""
    pass_number: int = 0


# A single, module-level instance — only one stream can run at a time, so
# there's no id-keyed job dict like the other modules use.
STREAM = StreamState()
