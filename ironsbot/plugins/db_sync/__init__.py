import asyncio
import os
import tempfile
from typing import NamedTuple

import httpx
from anyio import Path
from nonebot import get_driver, require
from nonebot.log import logger

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

from .manager import db_manager


class _SyncEntry(NamedTuple):
    sync_url: str
    sync_interval_minutes: int


_driver = get_driver()
_sync_locks: dict[str, asyncio.Lock] = {}
_registered_syncs: dict[str, _SyncEntry] = {}
_local_databases: set[str] = set()


def _get_lock(name: str) -> asyncio.Lock:
    if name not in _sync_locks:
        _sync_locks[name] = asyncio.Lock()
    return _sync_locks[name]


def register_database(
    name: str,
    *,
    sync_url: str,
    sync_interval_minutes: int = 60,
) -> None:
    """注册一个从远程同步的内存数据库。供其他插件在模块级代码中调用。

    该函数会：
    1. 在 db_manager 中注册内存引擎
    2. 添加定时同步任务
    3. 在启动时自动执行首次同步
    """
    if name in _registered_syncs or name in _local_databases:
        logger.warning(f"数据库 '{name}' 已注册，跳过重复注册")
        return

    db_manager.register(name)
    _registered_syncs[name] = _SyncEntry(sync_url, sync_interval_minutes)

    scheduler.add_job(
        sync_database,
        "interval",
        args=[name],
        minutes=sync_interval_minutes,
        id=f"db_sync_{name}",
        replace_existing=True,
    )
    logger.debug(f"已注册数据库 '{name}'，同步间隔: {sync_interval_minutes} 分钟")


def register_local_database(name: str, *, file_path: str) -> None:
    """注册一个从本地文件加载的只读内存数据库，不设置自动同步。"""
    if name in _registered_syncs or name in _local_databases:
        logger.warning(f"数据库 '{name}' 已注册，跳过重复注册")
        return

    db_manager.register(name)
    db_manager.load_from_file(name, file_path)
    _local_databases.add(name)
    logger.info(f"已从本地文件 '{file_path}' 加载数据库 '{name}'（无自动同步）")


async def sync_database(name: str) -> None:
    """从远程 URL 下载 SQLite 数据库并导入到内存中。"""
    entry = _registered_syncs.get(name)
    if not entry:
        return

    async with _get_lock(name):
        fd, tmp_name = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            logger.info(f"开始从 {entry.sync_url} 同步数据库 '{name}'...")

            content = bytearray()
            async with (
                httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=httpx.Timeout(30.0, read=120.0),
                ) as client,
                client.stream("GET", entry.sync_url) as response,
            ):
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    content.extend(chunk)

            await tmp_path.write_bytes(bytes(content))
            db_manager.load_from_file(name, str(tmp_path))

            size_mb = len(content) / (1024 * 1024)
            logger.info(f"数据库 '{name}' 已同步到内存，源文件大小: {size_mb:.2f} MB")

        except httpx.HTTPError:
            logger.exception(f"数据库 '{name}' 同步失败（HTTP 错误）")
        except (OSError, ValueError):
            logger.exception(f"数据库 '{name}' 同步失败（文件或导入错误）")
        finally:
            await tmp_path.unlink(missing_ok=True)


@_driver.on_startup
async def _on_startup() -> None:
    if not _registered_syncs:
        logger.debug("无已注册的同步数据库，db_sync 插件未激活")
        return

    for name, entry in _registered_syncs.items():
        logger.info(
            f"数据库 '{name}' 同步已启动，同步间隔: {entry.sync_interval_minutes} 分钟"
        )
        await sync_database(name)
