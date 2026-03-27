import re
from datetime import timedelta, timezone
from typing import NoReturn

import httpx
from nonebot.adapters import Bot, MessageTemplate
from nonebot.matcher import Matcher
from seerapi_models import ApiMetadataORM
from sqlmodel import select

from ironsbot.utils.rule import no_reply

from ..depends import SeerAPISession
from ..depends.image import PreviewImageGetter
from ..group import matcher_group

preview_matcher = matcher_group.on_fullmatch("下周预告", rule=no_reply())

PREVIEW_MESSAGE_TEMPLATE = MessageTemplate(
    "{image}\n预告图来自 https://github.com/WhY15w/seer-unity-preview-img-dumper"
)


@preview_matcher.handle()
async def handle_preview(matcher: Matcher, bot: Bot) -> NoReturn:
    image = await PreviewImageGetter.get("")
    await matcher.finish(PREVIEW_MESSAGE_TEMPLATE.format(image=await image.build(bot)))


data_version_matcher = matcher_group.on_fullmatch("数据版本", rule=no_reply())

DATA_VERSION_MESSAGE_TEMPLATE = MessageTemplate("数据更新时间：{time}")


@data_version_matcher.handle()
async def handle_data_version(matcher: Matcher, session: SeerAPISession) -> NoReturn:
    obj = session.exec(select(ApiMetadataORM)).first()
    if not obj:
        await matcher.finish("❌暂无数据版本信息(这是一个bug，请反馈给开发者)")
    dt = obj.generate_time
    # 为确保时区转换生效，需先判断dt是否带有tzinfo（即是否为"aware" datetime）；否则先转为UTC再转换
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # 假设dt原本为UTC时间（无tzinfo），先加上UTC tzinfo
        dt = dt.replace(tzinfo=timezone.utc)
    dt_local = dt.astimezone(timezone(timedelta(hours=8)))
    time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
    await matcher.finish(DATA_VERSION_MESSAGE_TEMPLATE.format(time=time_str))


async def fetch_server_notice_text() -> str | None:
    """获取服务器停服维护公告文本，若没有则返回None，一般来说如果返回了文本则表示服务器正在维护"""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://unity-notice.61.com/unity_notice/")
        resp.raise_for_status()
        data = resp.json()

    for item in data:
        if item["type"] == 3:
            text = item["text"]
            # 需要删除所有标签
            text = re.sub(r"<[^>]*>", "", text)
            return text.replace("\\n", "\n")
    return None


# async def notify_server_open() -> None:
#     text = await fetch_server_notice_text()
#     if not text:
#         target = TargetQQGroup(group_id=494873951)
#         await MessageFactory("赛尔号开服了！").send_to(target)
#         scheduler.remove_job("notify_server_open")


# scheduler.add_job(
#     notify_server_open,
#     "interval",
#     minutes=1,
#     id="notify_server_open",
#     replace_existing=True,
# )

server_info_matcher = matcher_group.on_fullmatch(
    ("开服查询", "开服了吗"), rule=no_reply()
)


@server_info_matcher.handle()
async def handle_server_info(matcher: Matcher) -> NoReturn:
    text = await fetch_server_notice_text()
    if text:
        await matcher.finish(text)

    await matcher.finish("开服了哦~")
