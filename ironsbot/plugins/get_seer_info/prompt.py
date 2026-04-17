from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast, overload

from nonebot.adapters import Event
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory
from seerapi_models.build_model import BaseResModel
from typing_extensions import NamedTuple

from ironsbot.utils import build_sub_line
from ironsbot.utils.matcher import (
    enter_prompt_loop as _enter_prompt_loop,
)
from ironsbot.utils.matcher import (
    prompt_session_manager,
    reject_with_rule,
)

from .depends import SeerAPISession
from .depends.db import Getter, SQLModelSession

T = TypeVar("T")


class PromptItem(NamedTuple, Generic[T]):
    name: str
    desc: str
    value: T
    is_sub_prompt: bool = False


@dataclass
class Prompt(Generic[T]):
    title: str
    items: list[PromptItem[T]]
    at_user_id: int | None = None

    def __post_init__(self) -> None:
        if not self.title.endswith("\n"):
            self.title = self.title + "\n"

    @overload
    def get(self, index: int) -> T | None: ...
    @overload
    def get(self, index: int, default: T) -> T: ...
    def get(self, index: int, default: T | None = None) -> T | None:
        try:
            return self.items[index - 1].value
        except IndexError:
            return default

    def get_item(self, index: int) -> PromptItem[T] | None:
        try:
            return self.items[index - 1]
        except IndexError:
            return None

    def build_message(self) -> str:
        msg = self.title
        for index, item in enumerate(self.items, start=1):
            text = f"{index}. {item.name}（{item.desc}）"
            if item.is_sub_prompt:
                msg += build_sub_line(texts=[text])
            else:
                msg += f"{text}\n"
        msg += "\n💬 输入序号选择 · 输入 0 退出（现在支持连续选择咯，快来试试吧~）"

        return msg


_M = TypeVar("_M", bound=BaseResModel)

PROMPT_STATE_KEY = "prompt"


def _is_digit_input(event: Event) -> bool:
    """只匹配纯数字消息（含 ``"0"``），用于限制临时 Matcher 的触发范围。"""
    return event.get_plaintext().strip().isdigit()


# ── run_preprocessor：任何 priority > 0 的 matcher 运行前自动失效旧 prompt ──


@run_preprocessor
async def _invalidate_prompt_on_command(matcher: Matcher, event: Event) -> None:
    if matcher.priority > 0:
        prompt_session_manager.invalidate(event.get_session_id())


# ── 公开 API ──


async def enter_prompt(
    matcher: Matcher,
    event: Event,
    state: T_State,
    prompt: "Prompt[Any]",
    resolver: Callable[[Any, Matcher, SQLModelSession], Awaitable[None]],
) -> None:
    """发送 Prompt 并进入选择循环（替代 ``matcher.got``）。

    创建一个带版本化数字 Rule 的临时 Matcher，
    只匹配数字输入，其余消息正常传播给其他 Matcher。
    当新命令触发时，版本号递增使旧 prompt 自动失效。

    在 ``handle()`` 末尾调用，本函数始终 raise ``FinishedException``。

    Args:
        matcher: 当前 Matcher 实例。
        event: 当前事件。
        state: 当前会话 state（会存入 prompt 数据）。
        prompt: Prompt 实例。
        resolver: 选择处理回调，签名
            ``(item, matcher, session) -> None``。
    """
    state[PROMPT_STATE_KEY] = prompt
    session_id = event.get_session_id()
    version = prompt_session_manager.acquire(session_id)
    rule = prompt_session_manager.make_rule(session_id, version, _is_digit_input)

    handler = _create_selection_handler(resolver, session_id, version)

    await _enter_prompt_loop(
        matcher,
        handlers=[handler],
        rule=rule,
        prompt=prompt.build_message(),
    )


def _create_selection_handler(
    resolver: Callable[[Any, Matcher, SQLModelSession], Awaitable[None]],
    session_id: str,
    version: int,
) -> Callable[..., Awaitable[None]]:
    """创建选择循环 handler（从 event 读取输入，不依赖 got）。"""

    async def _handler(
        matcher: Matcher,
        event: Event,
        state: T_State,
        session: SeerAPISession,
    ) -> None:
        if PROMPT_STATE_KEY not in state:
            raise FinishedException

        key_text = event.get_plaintext().strip()

        if key_text == "0":
            await matcher.finish("❌已退出查询")

        if not key_text.isdigit():
            raise FinishedException

        prompt = cast("Prompt[Any]", state[PROMPT_STATE_KEY])
        if (item := prompt.get_item(int(key_text))) is None:
            await matcher.finish("⚠️序号超出范围，已退出选择")

        await resolver(item, matcher, session)

        rule = prompt_session_manager.make_rule(session_id, version, _is_digit_input)
        await reject_with_rule(matcher, rule)

    return _handler


def simple_prompt_resolver(
    data_getter: Getter[_M],
    message_builder: Callable[[_M], Awaitable[MessageFactory]],
    entity_name: str,
) -> Callable[..., Awaitable[None]]:
    """为 ``enter_prompt`` 创建简单的解析回调。

    适用于 Prompt 值为数据库主键 ID 的常见场景：
    通过 ``data_getter`` 获取对象，
    再用 ``message_builder`` 构建回复。

    Args:
        data_getter: ``GetData`` 实例，通过
            ``.get(session, id)`` 从数据库获取对象。
        message_builder: 异步函数，将数据库对象构建为
            回复消息。
        entity_name: 实体中文名称，用于错误提示
            （如 ``"刻印"``、``"宠物"``）。
    """

    async def _resolver(
        item: PromptItem[int],
        matcher: Matcher,
        session: Any,
    ) -> None:
        obj = data_getter.get(session, item.value)
        if not obj:
            await matcher.finish(
                message=f"❌未找到{entity_name} {item.value}（这是一个bug，请反馈给开发者）"
            )
        msg = await message_builder(obj)
        await msg.send()

    return _resolver
