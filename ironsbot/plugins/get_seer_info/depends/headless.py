from nonebot import require
from nonebot.matcher import Matcher
from nonebot.params import Depends

require("ironsbot.plugins.headless_seer")

from ironsbot.plugins.headless_seer.exception import (
    ClientNotInitializedError,
    NotLoggedInError,
)
from ironsbot.plugins.headless_seer.game import SeerGame
from ironsbot.plugins.headless_seer.manager import client_manager


async def _get_game_client(matcher: Matcher) -> SeerGame:
    try:
        return client_manager.get_client()
    except ClientNotInitializedError:
        await matcher.finish("❌无头客户端未运行，无法使用此命令")
    except NotLoggedInError:
        await matcher.finish("❌ 无头客户端尚未登录，无法使用此命令！")


GameClient = Depends(_get_game_client)
