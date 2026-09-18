"""Importing this module runs every module manifest's registration
side-effect (`main.py` imports it purely for that side effect)."""

from ..app_combinator import manifest as _combinator_manifest  # noqa: F401
from ..app_concat import manifest as _concat_manifest  # noqa: F401
from ..app_download import manifest as _download_manifest  # noqa: F401
from ..app_filter import manifest as _filter_manifest  # noqa: F401
from ..app_materials import manifest as _materials_manifest  # noqa: F401
from ..app_reframe import manifest as _reframe_manifest  # noqa: F401
from ..app_s3file import manifest as _s3file_manifest  # noqa: F401
