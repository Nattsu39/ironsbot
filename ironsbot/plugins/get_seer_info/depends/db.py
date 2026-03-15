import re
from collections.abc import Callable
from typing import Annotated, Any, Generic, TypeVar

from nonebot.params import Depends
from seerapi_models import (
    GemCategoryORM,
    GemORM,
    MintmarkClassCategoryORM,
    MintmarkORM,
    PetORM,
    PetSkinORM,
)
from sqlalchemy import func
from sqlmodel import SQLModel, col, select

from ironsbot.utils.parse_arg import parse_string_arg

from ..db import SQLModelSession, get_session

T = TypeVar("T", bound=SQLModel)

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


Session = Annotated[SQLModelSession, Depends(get_session)]


class GetData(Generic[T]):
    def __init__(
        self,
        model: type[T],
        *,
        name_column: str = "name",
        arg_postprocess: Callable[[str], str] = str.strip,
    ) -> None:
        if not hasattr(model, name_column):
            raise ValueError(f"Model {model.__name__} has no {name_column} column")

        self.model = model
        self.name_column = getattr(model, name_column)
        self.arg_postprocess = arg_postprocess

    def get(self, session: SQLModelSession, id: int) -> T | None:
        return session.get(self.model, id)

    def __call__(
        self,
        session: Session,
        arg: str = Depends(parse_string_arg),
    ) -> list[T]:
        arg = self.arg_postprocess(arg)
        if arg.isdigit():
            obj = self.get(session, int(arg))
            if obj:
                return [obj]

            return []

        stripped_arg = _strip_special(arg)
        statement = select(self.model).where(
            _col_strip_special(col(self.name_column)).like(f"%{stripped_arg}%")
        )
        objs = session.exec(statement).all()
        return list(objs)


class GetPetDataByAlias(GetData[PetORM]):
    def __call__(
        self,
        session: Session,
        arg: str = Depends(parse_string_arg),
    ) -> list[PetORM]:
        arg = self.arg_postprocess(arg)

        stripped_arg = _strip_special(arg)
        statement = select(self.model).where(
            _col_strip_special(col(self.name_column)).like(f"%{stripped_arg}%")
        )
        objs = session.exec(statement).all()
        return list(objs)


PetDataGetter = GetData(PetORM)


def GetPetData() -> Any:
    return Depends(GetData(PetORM))


MintmarkDataGetter = GetData(MintmarkORM)


def GetMintmarkData() -> Any:
    return Depends(GetData(MintmarkORM))


MintmarkClassDataGetter = GetData(MintmarkClassCategoryORM)


def GetMintmarkClassData() -> Any:
    return Depends(GetData(MintmarkClassCategoryORM))


PetSkinDataGetter = GetData(PetSkinORM)


def GetPetSkinData() -> Any:
    return Depends(GetData(PetSkinORM))


GemDataGetter = GetData(GemORM)


def GetGemData() -> Any:
    return Depends(GetData(GemORM))


GemCategoryDataGetter = GetData(GemCategoryORM)


def GetGemCategoryData() -> Any:
    return Depends(GetData(GemCategoryORM))
