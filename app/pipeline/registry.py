from .manifest import ModuleManifest

MODULES: dict[str, ModuleManifest] = {}


def register(manifest: ModuleManifest) -> None:
    MODULES[manifest.id] = manifest
