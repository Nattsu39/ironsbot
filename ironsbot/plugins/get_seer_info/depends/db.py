# ruff: noqa: N802

import re
from collections.abc import Callable, Generator, Iterable
from typing import Annotated, Any, Generic, Protocol, TypeVar

from nonebot import logger, require
from nonebot.params import Depends
from seerapi_models import (
    GemCategoryORM,
    GemORM,
    MintmarkClassCategoryORM,
    MintmarkORM,
    PetORM,
    PetSkinORM,
)
from seerapi_models.build_model import BaseResModel
from sqlmodel import Session as SQLModelSession
from sqlmodel import col, func, select

from ..config import plugin_config
from ..orm import BaseAliasORM, GemAliasORM, PetAliasORM

require("ironsbot.plugins.db_sync")

from ironsbot.plugins.db_sync import register_database, register_local_database
from ironsbot.plugins.db_sync.manager import db_manager
from ironsbot.utils.parse_arg import parse_string_arg

_SEERAPI_DB = "seerapi"
_ALIAS_DB = "aliases"


def _register(name: str, sync_url: str, interval: int, local_path: str) -> None:
    if sync_url:
        register_database(name, sync_url=sync_url, sync_interval_minutes=interval)
    else:
        register_local_database(name, file_path=local_path)


_register(
    _SEERAPI_DB,
    plugin_config.seerapi_sync_url,
    plugin_config.seerapi_sync_interval_minutes,
    plugin_config.seerapi_local_path,
)
_register(
    _ALIAS_DB,
    plugin_config.alias_sync_url,
    plugin_config.alias_sync_interval_minutes,
    plugin_config.alias_local_path,
)

_T_Model = TypeVar("_T_Model", bound=BaseResModel)

_IGNORED_CHARS = ".·・•‧∙⋅。—\u2013-_/ "
_IGNORED_CHARS_PATTERN = re.compile(f"[{re.escape(_IGNORED_CHARS)}]")


def _strip_special(text: str) -> str:
    return _IGNORED_CHARS_PATTERN.sub("", text)


def _col_strip_special(column: Any) -> Any:
    """构建一个 SQL 表达式，将列中的特殊字符逐个替换为空字符串。"""
    expr = column
    for char in _IGNORED_CHARS:
        expr = func.replace(expr, char, "")
    return expr


def _session_factory(
    db_name: str,
) -> Callable[[], Generator[SQLModelSession, Any, None]]:
    def _session_generator() -> Generator[SQLModelSession, Any, None]:
        yield from db_manager.get_session(db_name)

    return _session_generator


SeerAPISession = Annotated[SQLModelSession, Depends(_session_factory(_SEERAPI_DB))]
AliasSession = Annotated[SQLModelSession, Depends(_session_factory(_ALIAS_DB))]
AllSessions = Annotated[
    dict[str, SQLModelSession], Depends(db_manager.get_all_sessions)
]


class IdSelector(Protocol):
    db_name: str

    def __call__(self, session: SQLModelSession, arg: str) -> set[int]: ...


class AliasSelector(IdSelector):
    __slots__ = ("db_name", "model")

    def __init__(self, *, db_name: str, model: type[BaseAliasORM]) -> None:
        self.db_name = db_name
        self.model = model

    def __repr__(self) -> str:
        return f"AliasSelector(db_name={self.db_name}, model={self.model.__name__})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, AliasSelector)
            and self.db_name == other.db_name
            and self.model == other.model
        )

    def __hash__(self) -> int:
        return hash((self.db_name, self.model))

    def __call__(
        self,
        session: AliasSession,
        arg: str = Depends(parse_string_arg),
    ) -> set[int]:
        stripped_arg = arg.strip()
        statement = select(self.model).where(
            _col_strip_special(col(self.model.name)).like(f"%{stripped_arg}%")
        )
        aliases = session.exec(statement).all()
        return {alias.target_id for alias in aliases}


class NameSelector(IdSelector):
    __slots__ = ("db_name", "model", "name_column")

    def __init__(
        self,
        *,
        db_name: str,
        model: type[_T_Model],
        name_column: str = "name",
    ) -> None:
        self.db_name = db_name
        if not hasattr(model, name_column):
            raise ValueError(
                f"Model {model.resource_name()} has no {name_column} column"
            )

        self.model = model
        self.name_column = getattr(model, name_column)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, NameSelector)
            and self.db_name == other.db_name
            and self.model == other.model
            and self.name_column == other.name_column
        )

    def __hash__(self) -> int:
        return hash((self.db_name, self.model, self.name_column))

    def __repr__(self) -> str:
        return (
            "NameSelector("
            f"db_name={self.db_name!r}, "
            f"model={self.model.resource_name()!r}, "
            f"name_column={self.name_column!r}"
            ")"
        )

    def __call__(
        self,
        session: SeerAPISession,
        arg: str = Depends(parse_string_arg),
    ) -> set[int]:
        if arg.isdigit():
            return {int(arg)}

        stripped_arg = _strip_special(arg)
        statement = select(self.model.id).where(
            _col_strip_special(col(self.name_column)).like(f"%{stripped_arg}%")
        )

        return set(session.exec(statement).all())


class Getter(Generic[_T_Model]):
    __slots__ = ("model", "selectors")

    def __init__(self, model: type[_T_Model], *selectors: IdSelector) -> None:
        self.model = model
        self.selectors = set(selectors)

    def get_ids(self, sessions: AllSessions, arg: str) -> set[int]:
        ids = set()
        for selector in self.selectors:
            if selector.db_name not in sessions:
                logger.warning(f"{selector!r}: 未找到数据库会话")
                continue

            ids |= selector(sessions[selector.db_name], arg)

        return ids

    def get(self, session: SQLModelSession, id_: int) -> _T_Model | None:
        return session.get(self.model, id_)

    def get_multiple(
        self, session: SQLModelSession, ids: Iterable[int]
    ) -> tuple[_T_Model, ...]:
        return tuple(
            session.exec(select(self.model).where(col(self.model.id).in_(ids))).all()
        )

    def __call__(
        self, sessions: AllSessions, arg: str = Depends(parse_string_arg)
    ) -> tuple[_T_Model, ...]:
        ids = self.get_ids(sessions, arg)
        return self.get_multiple(sessions[_SEERAPI_DB], ids)

    def __and__(self, other: "Getter[_T_Model]") -> "Getter[_T_Model]":
        if not isinstance(other, Getter):
            raise TypeError(f"Cannot combine Getter with {type(other)}")

        return Getter(
            self.model,
            *self.selectors,
            *other.selectors,
        )

    def __rand__(self, other: "Getter[_T_Model]") -> "Getter[_T_Model]":
        if not isinstance(other, Getter):
            raise TypeError(f"Cannot combine Getter with {type(other)}")

        return Getter(
            self.model,
            *other.selectors,
            *self.selectors,
        )


PetDataGetter = Getter(
    PetORM,
    NameSelector(db_name=_SEERAPI_DB, model=PetORM),
    AliasSelector(db_name=_ALIAS_DB, model=PetAliasORM),
)


def GetPetData() -> Any:
    return Depends(PetDataGetter)


MintmarkDataGetter = Getter(
    MintmarkORM,
    NameSelector(db_name=_SEERAPI_DB, model=MintmarkORM),
)


def GetMintmarkData() -> Any:
    return Depends(MintmarkDataGetter)


MintmarkClassDataGetter = Getter(
    MintmarkClassCategoryORM,
    NameSelector(db_name=_SEERAPI_DB, model=MintmarkClassCategoryORM),
)


def GetMintmarkClassData() -> Any:
    return Depends(MintmarkClassDataGetter)


PetSkinDataGetter = Getter(
    PetSkinORM,
    NameSelector(db_name=_SEERAPI_DB, model=PetSkinORM),
)


def GetPetSkinData() -> Any:
    return Depends(PetSkinDataGetter)


GemDataGetter = Getter(
    GemORM,
    NameSelector(db_name=_SEERAPI_DB, model=GemORM),
    AliasSelector(db_name=_ALIAS_DB, model=GemAliasORM),
)


def GetGemData() -> Any:
    return Depends(GemDataGetter)


GemCategoryDataGetter = Getter(
    GemCategoryORM,
    NameSelector(db_name=_SEERAPI_DB, model=GemCategoryORM),
)


def GetGemCategoryData() -> Any:
    return Depends(GemCategoryDataGetter)
