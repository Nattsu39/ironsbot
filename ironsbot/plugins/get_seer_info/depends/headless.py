from nonebot import require
from nonebot.params import Depends

require("ironsbot.plugins.headless_seer")

from ironsbot.plugins.headless_seer.game import SeerGame
from ironsbot.plugins.headless_seer.manager import client_manager


async def _get_game_client() -> SeerGame:
    return client_manager.get_client()


GameClient = Depends(_get_game_client)
