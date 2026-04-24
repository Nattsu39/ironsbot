import importlib
import pkgutil

from nonebot import logger
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor

from ironsbot.plugins.db_sync.manager import db_manager
from ironsbot.plugins.headless_seer.exception import SocketRecvError

from ..depends.db import ErrorCodeGetter

__all__ = []

# 自动导入本目录下所有非私有模块
for _, module_name, __ in pkgutil.iter_modules(__path__):
    if not module_name.startswith("_"):
        try:
            importlib.import_module(f".{module_name}", __name__)
        except ImportError:
            logger.opt(exception=True).error(f"模块 {module_name} 导入失败")
            continue

        __all__ += [module_name]  # noqa: PLE0604


@run_postprocessor
async def do_something(matcher: Matcher, exception: Exception | None):
    if isinstance(exception, SocketRecvError):
        sessions = next(db_manager.get_all_sessions())
        result_code = exception.head.result
        error_code = ErrorCodeGetter(sessions, str(result_code))
        if error_code:
            await matcher.finish(f"❌ 请求失败：{error_code[0].message}")
        else:
            await matcher.finish(f"❌ 请求失败，错误码：{result_code}")
