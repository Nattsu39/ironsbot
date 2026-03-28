from nonebot import get_driver, logger

from .config import plugin_config
from .manager import client_manager

_driver = get_driver()


@_driver.on_startup
async def _on_startup() -> None:
    if (
        plugin_config.headless_seer_user_id is None
        or plugin_config.headless_seer_password is None
    ):
        logger.warning("无头客户端未配置用户名或密码，跳过登录")
        return
    try:
        await client_manager.login(
            user_id=plugin_config.headless_seer_user_id,
            password=plugin_config.headless_seer_password,
            login_server_url=plugin_config.headless_seer_login_server_addr,
            heartbeat_interval=plugin_config.headless_seer_heartbeat_interval,
            reconnect_retries=plugin_config.headless_seer_reconnect_retries,
            reconnect_delay=plugin_config.headless_seer_reconnect_delay,
            reconnect_delay_max=plugin_config.headless_seer_reconnect_delay_max,
        )
    except Exception:
        logger.opt(exception=True).error("无头客户端登录失败")


@_driver.on_shutdown
async def _on_shutdown() -> None:
    client_manager.shutdown()
