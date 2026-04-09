import importlib
import pkgutil

from nonebot import logger

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
