from ..command_id import COMMAND_ID
from ..core.register import packet_register
from .login import AllSvrListInfo, RangeSvrInfo
from .team import SimpleTeamInfo

packet_register[COMMAND_ID.COMMEND_ONLINE] = AllSvrListInfo
packet_register[COMMAND_ID.RANGE_ONLINE] = RangeSvrInfo
packet_register[COMMAND_ID.TEAM_GET_INFO] = SimpleTeamInfo
