from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast, overload

from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory
from seerapi_models.build_model import BaseResModel
from typing_extensions import NamedTuple

from ironsbot.utils import build_sub_line

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
        # 如果title不是以换行符结尾，则添加换行符
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

    def build_message(self) -> MessageFactory:
        msg = MessageFactory()
        msg += self.title
        for index, item in enumerate(self.items, start=1):
            text = f"{index}. {item.name}（{item.desc}）"
            if item.is_sub_prompt:
                msg += build_sub_line(texts=[text])
            else:
                msg += f"{text}\n"
        msg += "\n💬 输入序号选择 · 输入 0 退出"

        return msg


_M = TypeVar("_M", bound=BaseResModel)

PROMPT_STATE_KEY = "prompt"


def create_prompt_got_handler(
    got_key: str,
    resolver: Callable[[Any, Matcher, SQLModelSession], Awaitable[None]],
) -> Callable[[Matcher, T_State, SeerAPISession], Awaitable[None]]:
    """为 ``matcher.got()`` 创建处理 Prompt 选择的 handler。

    工厂负责 Prompt 选择的通用逻辑（解析输入、退出、查找值），
    业务逻辑由 ``resolver`` 回调处理。

    Args:
        got_key: 与 ``matcher.got(key)`` 一致的 key，
            用于从 matcher 中取出用户输入的消息。
        resolver: 异步回调
            ``(item, matcher, session) -> None``，
            接收用户选择的 ``PromptItem``、当前
            Matcher 和数据库会话。回调应自行调用
            ``matcher.finish()`` 发送回复。
            可使用 ``simple_prompt_resolver`` 快速创建。

    用法::

        matcher.got("key", prompt=MessageTemplate("{prompt_message}"))(
            create_prompt_got_handler("key", my_resolver)
        )
    """

    async def _handler(
        matcher: Matcher,
        state: T_State,
        session: SeerAPISession,
    ) -> None:
        if PROMPT_STATE_KEY not in state:
            raise ValueError(f"Prompt not found in state: {state}")

        if (arg := matcher.get_arg(got_key)) is None:
            raise FinishedException

        if (key_text := arg.extract_plain_text()) == "0":
            await matcher.finish("❌已退出查询")

        if not key_text.isdigit():
            raise FinishedException

        prompt = cast("Prompt[Any]", state[PROMPT_STATE_KEY])
        if (item := prompt.get_item(int(key_text))) is None:
            raise FinishedException

        await resolver(item, matcher, session)

    return _handler


def simple_prompt_resolver(
    data_getter: Getter[_M],
    message_builder: Callable[[_M], Awaitable[MessageFactory]],
    entity_name: str,
) -> Callable[..., Awaitable[None]]:
    """为 ``create_prompt_got_handler`` 创建简单的解析回调。

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
                f"❌未找到{entity_name} {item.value}（这是一个bug，请反馈给开发者）"
            )
        msg = await message_builder(obj)
        await msg.finish()

    return _resolver
