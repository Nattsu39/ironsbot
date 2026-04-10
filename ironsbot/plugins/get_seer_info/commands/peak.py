from collections.abc import Iterable
from datetime import datetime
from typing import TYPE_CHECKING, TypedDict

from nonebot.matcher import Matcher
from nonebot_plugin_saa import Image, MessageFactory
from seerapi_models import PeakExpertPoolORM, PeakPoolORM, PeakPoolVoteORM
from sqlmodel import select

from ironsbot.plugins.headless_seer.game import SeerGame
from ironsbot.utils.rule import no_reply

from ..depends import GameClient, SeerAPISession
from ..group import matcher_group
from ..render import render_peak_pool, render_peak_pool_vote

if TYPE_CHECKING:
    from seerapi_models.pet import PetORM

    from ironsbot.plugins.headless_seer.packets import DailyRankList

peak_pool_matcher = matcher_group.on_fullmatch(
    ("竞技池", "巅峰竞技池"), rule=no_reply()
)


@peak_pool_matcher.handle()
async def handle_peak_pool(
    matcher: Matcher,
    session: SeerAPISession,
) -> None:
    statement = select(PeakPoolORM)
    pools = session.exec(statement).all()

    if not pools:
        await matcher.finish("❌找不到竞技池数据。（这是一个bug，请反馈给开发者）")

    await matcher.send("正在生成图片...")
    start_time = pools[0].start_time.strftime("%Y-%m-%d")
    end_time = pools[0].end_time.strftime("%Y-%m-%d")
    pic_bytes = await render_peak_pool(pools, f"竞技池 / {start_time} ~ {end_time}")
    msg = MessageFactory()
    msg += Image(pic_bytes)
    await msg.finish(at_sender=False)


peak_expert_pool_matcher = matcher_group.on_fullmatch(
    ("专家池", "巅峰专家池"), rule=no_reply()
)


@peak_expert_pool_matcher.handle()
async def handle_peak_expert_pool(
    matcher: Matcher,
    session: SeerAPISession,
) -> None:
    statement = select(PeakExpertPoolORM)
    pools = session.exec(statement).all()
    if not pools:
        await matcher.finish("❌找不到专家池数据。（这是一个bug，请反馈给开发者）")

    await matcher.send("正在生成图片...")
    start_time = pools[0].start_time.strftime("%Y-%m-%d")
    end_time = pools[0].end_time.strftime("%Y-%m-%d")
    pic_bytes = await render_peak_pool(pools, f"专家禁用池 / {start_time} ~ {end_time}")
    msg = MessageFactory()
    msg += Image(pic_bytes)
    await msg.finish(at_sender=False)


peak_vote_matcher = matcher_group.on_fullmatch(
    ("巅峰投票", "巅峰票选", "巅峰池票选"), rule=no_reply()
)


class _VoteRank(TypedDict):
    content: "DailyRankList"
    title: str
    pets: "list[PetORM]"


def sort_peak_pool_vote_by_time(
    pool_list: Iterable[PeakPoolVoteORM],
) -> list[PeakPoolVoteORM]:
    """
    根据当前时间对投票模型排序，距离当前时间近的排在前面。
    支持对象拥有 start_time 属性（datetime 类型）。
    """
    now = datetime.now()

    def time_distance(obj: PeakPoolVoteORM) -> float:
        return abs((obj.start_time - now).total_seconds())

    return sorted(pool_list, key=time_distance)


@peak_vote_matcher.handle()
async def handle_peak_vote(
    matcher: Matcher,
    session: SeerAPISession,
    game: SeerGame = GameClient,
) -> None:
    pools: list[_VoteRank] = []
    now = datetime.now()
    for orm in sort_peak_pool_vote_by_time(session.exec(select(PeakPoolVoteORM)).all()):
        title = f"限{orm.count}池票选"
        if orm.start_time > now:
            title += " / 票选未开始"
        elif orm.end_time < now:
            title += " / 票选已结束"
        else:
            title += f"<br>票选时间：{orm.start_time.strftime('%Y-%m-%d')} ~ {orm.end_time.strftime('%Y-%m-%d')}"

        if orm.count == 2:
            pool = await game.get_limit_pool_vote(sub_key=orm.subkey)
        elif orm.count == 3:
            pool = await game.get_semi_limit_pool_vote(sub_key=orm.subkey)
        else:
            continue

        pools.append(
            {
                "content": pool,
                "title": title,
                "pets": orm.pet,
            }
        )

    if not pools:
        await matcher.finish("❌找不到票选数据。")

    await matcher.send("正在生成图片...")
    pic_bytes = await render_peak_pool_vote(pools)
    msg = MessageFactory()
    msg += Image(pic_bytes)
    await msg.finish(at_sender=False)
