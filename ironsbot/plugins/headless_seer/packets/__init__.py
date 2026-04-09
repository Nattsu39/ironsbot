from ..command_id import COMMAND_ID
from ..core.register import packet_register
from .login import AllSvrListInfo, RangeSvrInfo
from .peak import DailyRankList
from .team import SimpleTeamInfo
from .user import MoreInfo, OnLineInfo, OnLineInfos, UserForeverValue, UserInfo

packet_register[COMMAND_ID.COMMEND_ONLINE] = AllSvrListInfo
packet_register[COMMAND_ID.RANGE_ONLINE] = RangeSvrInfo
packet_register[COMMAND_ID.TEAM_GET_INFO] = SimpleTeamInfo
packet_register[COMMAND_ID.GET_DAILY_RANK_INFO] = DailyRankList
packet_register[COMMAND_ID.GET_USER_INFO] = UserInfo
packet_register[COMMAND_ID.GET_MORE_USER_INFO] = MoreInfo
packet_register[COMMAND_ID.USER_FOREVER_VALUE] = UserForeverValue
packet_register[COMMAND_ID.SEE_ONLINE] = OnLineInfos


__all__ = [
    "AllSvrListInfo",
    "DailyRankList",
    "MoreInfo",
    "OnLineInfo",
    "OnLineInfos",
    "RangeSvrInfo",
    "SimpleTeamInfo",
    "UserForeverValue",
    "UserInfo",
]
