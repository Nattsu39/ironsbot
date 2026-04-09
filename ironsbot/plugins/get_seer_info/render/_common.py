import base64
from pathlib import Path

from nonebot import require

require(name="nonebot_plugin_htmlkit")

TEMPLATES_PATH = Path(__file__).parent.parent / "templates"


def to_data_uri(data: bytes, mime_type: str = "image/png") -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"
