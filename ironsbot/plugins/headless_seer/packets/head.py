from typing import Annotated

from ..packet.fields import Int, UInt, Unicode
from ..packet.packet import Deserializable
from ..type_hint import CommandID


class HeadInfo(Deserializable):
    version: Annotated[str, Unicode[1]]
    cmd_id: Annotated[CommandID, UInt]
    user_id: UInt
    result: Int
