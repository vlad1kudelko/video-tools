from enum import Enum


class PortType(str, Enum):
    """Canonical data-shaped port types. Only what the 4 manifested modules
    actually need — no speculative ImageFile/AudioFile types until a module
    needs one."""

    TEXT_FILE = "text_file"
    VIDEO_FILE = "video_file"
    VIDEO_FILE_LIST = "video_file_list"
