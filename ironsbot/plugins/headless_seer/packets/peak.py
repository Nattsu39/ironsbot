from typing import Annotated

import ironsbot.plugins.headless_seer.packet.fields as f

from ..packet.packet import Deserializable


class DailyRankInfo(Deserializable):
    id: f.UInt
    score: f.Int
    nick: Annotated[str, f.Unicode[16]]


class DailyRankList(Deserializable):
    count: f.UInt
    rank_list: Annotated[
        list[DailyRankInfo], f.Array[f.size_by("count"), DailyRankInfo]
    ]


class DailyRankParam(Deserializable):
    key: f.UInt
    sub_key: f.UInt
    start: f.UInt
    end: f.UInt
