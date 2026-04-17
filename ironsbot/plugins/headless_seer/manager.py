from typing import Final

from nonebot import logger

from .exception import NotLoggedInError
from .game import SeerGame


class ClientManager:
    """管理 SeerGame 实例的单例管理器。

    通过 login/logout 控制默认客户端的生命周期，
    供 NoneBot 事件处理器通过 get_client() 获取。
    """

    def __init__(self) -> None:
        self._client: SeerGame | None = None

    def get_client(self) -> SeerGame:
        """获取已登录的游戏客户端，未登录时抛出 NotLoggedInError。"""
        if self._client is None or not self._client.is_logged_in:
            raise NotLoggedInError("无头客户端尚未登录")
        return self._client

    async def login(
        self,
        user_id: int,
        password: str,
        login_server_url: str,
        *,
        heartbeat_interval: float | None = None,
        reconnect_retries: int = 0,
        reconnect_delay: float = 5.0,
        reconnect_delay_max: float = 120.0,
    ) -> SeerGame:
        game = SeerGame(
            user_id,
            password,
            login_server_url=login_server_url,
            heartbeat_interval=heartbeat_interval,
            reconnect_retries=reconnect_retries,
            reconnect_delay=reconnect_delay,
            reconnect_delay_max=reconnect_delay_max,
        )
        self._client = game
        try:
            await game.login()
            logger.info(f"无头客户端已登录，米米号: {user_id}")
        except Exception:
            if reconnect_retries > 0:
                logger.opt(exception=True).warning(
                    "无头客户端初始登录失败，将尝试自动重连"
                )
                game.schedule_reconnect()
            else:
                self._client = None
                raise
        return game

    def shutdown(self) -> None:
        if self._client is not None:
            self._client.logout()
            logger.info("无头客户端已断开连接")
            self._client = None


client_manager: Final[ClientManager] = ClientManager()
