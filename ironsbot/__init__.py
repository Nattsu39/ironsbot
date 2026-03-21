from importlib.metadata import version

try:
    __version__ = version("ironsbot")
except Exception:  # pragma: no cover
    __version__ = None
