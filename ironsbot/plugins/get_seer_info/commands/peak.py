from nonebot.matcher import Matcher
from nonebot_plugin_saa import Image, MessageFactory
from seerapi_models import PeakExpertPoolORM, PeakPoolORM
from sqlmodel import select

from ironsbot.utils.rule import no_reply

from ..depends import SeerAPISession
from ..group import matcher_group
from ..render import render_peak_pool

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


# peak_vote_matcher = matcher_group.on_fullmatch(
#     ("巅峰投票", "巅峰池票选"), rule=no_reply()
# )


# class _VoteRank(TypedDict):
#     content: "DailyRankList"
#     title: str


# @peak_vote_matcher.handle()
# async def handle_peak_vote(
#     matcher: Matcher,
#     session: SeerAPISession,
#     game: SeerGame = GameClient,
# ) -> None:
#     pools: list[_VoteRank] = []
#     for orm in session.exec(select(PeakPoolVoteORM)):
#         pool = await game.get_limit_pool_vote(sub_key=orm.subkey)
#         pools.append(
#             {
#                 "content": pool,
#                 "title": f"巅峰池票选 / {orm.start_time.strftime('%Y-%m-%d')} ~ {orm.end_time.strftime('%Y-%m-%d')}",
#             }
#         )

#     if not pools:
#         await matcher.finish("❌找不到票选数据。")

#     await matcher.send("正在生成图片...")
#     pic_bytes = await render_peak_pool_vote(pools)
#     msg = MessageFactory()
#     msg += Image(pic_bytes)
#     await msg.finish(at_sender=False)
