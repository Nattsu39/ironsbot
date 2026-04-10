import asyncio
from collections.abc import Sequence
from typing import TypedDict

from nonebot_plugin_htmlkit import template_to_pic
from seerapi_models import PeakExpertPoolORM, PeakPoolORM

from ..depends.image import ElementTypeImageGetter, PetHeadImageGetter
from ._common import TEMPLATES_PATH, to_data_uri

TEMPLATE_PATH = TEMPLATES_PATH / "peak_pool"
SHARED_PATH = TEMPLATES_PATH / "_shared"

CELL_WIDTH = 100 + 2 * 2  # pet-cell width + border
CELL_GAP = 10
POOL_OVERHEAD = 18 * 2 + 1 * 2  # pool-section padding + border
CONTAINER_PADDING = 20 * 2
MAX_COLS = 10


class PetInPoolDict(TypedDict):
    id: int
    name: str
    head_img: str
    type_icon: str


class PoolDict(TypedDict):
    id: int
    count: int
    pets: list[PetInPoolDict]


async def render_peak_pool(
    pools: Sequence[PeakPoolORM | PeakExpertPoolORM], pool_type: str
) -> bytes:
    """渲染巅峰池信息卡片图片，返回 PNG 图片字节"""
    unique_rids: dict[str, None] = {}
    unique_type_ids: dict[int, None] = {}

    for pool in pools:
        for pet in pool.pet:
            unique_rids.setdefault(str(pet.resource_id), None)
            unique_type_ids.setdefault(pet.type.id, None)

    rid_list = list(unique_rids)
    type_id_list = list(unique_type_ids)

    results = await asyncio.gather(
        *(PetHeadImageGetter.get_bytes(rid) for rid in rid_list),
        *(ElementTypeImageGetter.get_bytes(str(tid)) for tid in type_id_list),
    )

    head_bytes_list = results[: len(rid_list)]
    type_bytes_list = results[len(rid_list) :]

    head_data_uris: dict[str, str] = {
        rid: to_data_uri(data)
        for rid, data in zip(rid_list, head_bytes_list, strict=True)
    }
    type_data_uris: dict[int, str] = {
        tid: to_data_uri(data)
        for tid, data in zip(type_id_list, type_bytes_list, strict=True)
    }

    pool_dicts: list[PoolDict] = []
    for pool in pools:
        pets: list[PetInPoolDict] = [
            {
                "id": pet.id,
                "name": pet.name,
                "head_img": head_data_uris[str(pet.resource_id)],
                "type_icon": type_data_uris[pet.type.id],
            }
            for pet in pool.pet
        ]
        pool_dicts.append(
            {
                "id": pool.id,
                "count": pool.count,
                "pets": pets,
            }
        )

    max_pets = max(len(p.pet) for p in pools)
    cols = min(max_pets, MAX_COLS)
    grid_width = cols * CELL_WIDTH + (cols - 1) * CELL_GAP
    max_width = grid_width + POOL_OVERHEAD + CONTAINER_PADDING

    return await template_to_pic(
        template_path=[TEMPLATE_PATH, SHARED_PATH],
        template_name="template.html",
        templates={
            "pools": pool_dicts,
            "pool_type": pool_type,
        },
        max_width=max_width + 20,
        allow_refit=False,
    )
