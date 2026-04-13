from collections.abc import Iterable


def build_sub_line(prefix: str = " ↳ ", *, texts: Iterable[str]) -> str:
    return "".join([f"{prefix}{text}\n" for text in texts])


__all__ = [
    "build_sub_line",
]
