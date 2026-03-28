from typing import TYPE_CHECKING, Any, Final, NamedTuple

from .type_hint import CommandID

if TYPE_CHECKING:
    from .packets.login import AllSvrListInfo, RangeSvrInfo
    from .packets.team import SimpleTeamInfo


class CommandIDNamedTuple(NamedTuple):
    GET_VERIFCODE: CommandID[Any] = CommandID(101)
    MAIN_LOGIN_IN: CommandID[Any] = CommandID(103)
    COMMEND_ONLINE: CommandID["AllSvrListInfo"] = CommandID(105)
    RANGE_ONLINE: CommandID["RangeSvrInfo"] = CommandID(106)
    CREATE_ROLE: CommandID[Any] = CommandID(108)
    SYS_ROLE: CommandID[Any] = CommandID(109)
    FENGHAO_TIME: CommandID[Any] = CommandID(111)

    LOGIN_IN: CommandID[Any] = CommandID(1001)
    GET_SESSION: CommandID[Any] = CommandID(1016)
    SEE_ONLINE: CommandID[Any] = CommandID(2157)

    TEAM_GET_INFO: CommandID["SimpleTeamInfo"] = CommandID(2917)

    SOCKET_RECONNECT: CommandID[Any] = CommandID(41463)


COMMAND_ID: Final[CommandIDNamedTuple] = CommandIDNamedTuple()
