import asyncio
from typing import Any, Literal, TypedDict

from nonebot_plugin_htmlkit import template_to_pic
from seerapi_models import GlossaryEntryORM, PetORM, SkillInPetORM, SoulmarkORM

from ironsbot.utils.analyze_parser import AnalyzeDescParser

from ..depends.image import (
    ElementTypeImageGetter,
    PetBodyImageGetter,
    PetHeadImageGetter,
)
from ._common import ANALYZE_DESC_STYLES, TEMPLATES_PATH, to_data_uri

TEMPLATE_PATH = TEMPLATES_PATH / "pet_info"

STAT_BAR_MAX_WIDTH = 120
STAT_MAX_VALUE = 200


class SkillDict(TypedDict):
    id: int
    name: str
    type_id: int
    type_name: str
    category_id: int
    category_name: str
    power: int
    max_pp: int
    accuracy: int | Literal["必中"]
    crit_rate: float | None
    priority: int
    must_hit: bool
    info: str | None
    learning_level: int | None
    is_special: bool
    is_advanced: bool
    is_fifth: bool
    effects: list[dict[str, Any]]
    activation_item: str | None
    friend_bonus: bool
    hide_effect_desc: str | None


class GlossaryDict(TypedDict):
    name: str
    desc: str


class SoulmarkDict(TypedDict):
    desc: str
    intensified: bool
    is_adv: bool
    pve_effective: bool | None
    tags: list[str]
    glossaries: list[GlossaryDict]


def _extract_skill(skill_in_pet: SkillInPetORM) -> list[SkillDict]:
    skill = skill_in_pet.skill
    effects = [
        {
            "id": e.effect_id,
            "info": AnalyzeDescParser(e.analyze_info).to_html(ANALYZE_DESC_STYLES),
        }
        for e in skill.skill_effect
    ]
    skill_activation_item = (
        skill_in_pet.skill_activation_item.name
        if skill_in_pet.skill_activation_item
        else None
    )
    hide_effect_desc = skill.hide_effect.description if skill.hide_effect else None
    result = SkillDict(
        id=skill.id,
        name=skill.name,
        type_id=skill.type.id,
        type_name=skill.type.name,
        category_id=skill.category.id,
        category_name=skill.category.name,
        power=skill.power,
        max_pp=skill.max_pp,
        accuracy="必中" if skill.must_hit else skill.accuracy,
        crit_rate=skill.crit_rate,
        priority=skill.priority,
        must_hit=skill.must_hit,
        info=skill.info,
        learning_level=skill_in_pet.learning_level,
        is_special=skill_in_pet.is_special,
        is_advanced=skill_in_pet.is_advanced,
        is_fifth=skill_in_pet.is_fifth,
        effects=effects,
        activation_item=skill_activation_item,
        friend_bonus=False,
        hide_effect_desc=hide_effect_desc,
    )
    if len(skill.friend_skill_effect) > 0:
        friend_skill: SkillDict = {
            **result,
            "friend_bonus": True,
            "is_special": True,
            "effects": [
                {"id": e.effect_id, "info": e.info} for e in skill.friend_skill_effect
            ],
        }
        return [result, friend_skill]

    return [result]


def _extract_soulmark(
    sm: SoulmarkORM, glossaries: list[GlossaryEntryORM]
) -> SoulmarkDict:
    tags = [t.name for t in sm.tag] if sm.tag else []
    desc_parser = AnalyzeDescParser(sm.analyze_desc or sm.desc)
    desc = desc_parser.to_html(ANALYZE_DESC_STYLES)
    return {
        "desc": desc,
        "intensified": sm.intensified,
        "is_adv": sm.is_adv,
        "pve_effective": sm.pve_effective,
        "tags": tags,
        "glossaries": [
            {"name": g.name, "desc": g.desc} for g in glossaries if g.name in desc
        ],
    }


async def render_pet_info(pet: PetORM) -> bytes:
    """渲染精灵信息卡片图片，返回 PNG 图片字节"""
    base_stats = pet.base_stats.to_model().round()
    stats = base_stats.model_dump()
    advance_stats = None
    if pet.advance:
        advance_stats = pet.advance.base_stats.to_model().round().model_dump()
    soulmarks = [_extract_soulmark(sm, pet.glossary_entry) for sm in pet.soulmark]

    all_skills: list[SkillDict] = [
        skill
        for skill_list in [_extract_skill(sl) for sl in pet.skill_links]
        for skill in skill_list
        if skill["id"] != 19002
    ]
    special_skills: list[SkillDict] = []
    advanced_skills: list[SkillDict] = []
    fifth_skills: list[SkillDict] = []
    level_skills: list[SkillDict] = []
    for skill in all_skills:
        if skill["is_fifth"]:
            fifth_skills.append(skill)
        elif skill["is_advanced"]:
            advanced_skills.append(skill)
        elif skill["is_special"]:
            special_skills.append(skill)
        else:
            level_skills.append(skill)

    level_skills.sort(key=lambda s: s["learning_level"] or 0, reverse=True)

    type_ids = list({skill["type_id"] for skill in all_skills} | {pet.type.id})

    pet_head_bytes, pet_body_bytes, *type_icon_results = await asyncio.gather(
        PetHeadImageGetter.get_bytes(str(pet.resource_id)),
        PetBodyImageGetter.get_bytes(str(pet.resource_id)),
        *(ElementTypeImageGetter.get_bytes(str(tid)) for tid in type_ids),
        ElementTypeImageGetter.get_bytes("prop"),
    )

    type_icons: dict[int | str, str] = {
        tid: to_data_uri(data)
        for tid, data in zip(type_ids, type_icon_results[:-1], strict=True)
    }
    type_icons["prop"] = to_data_uri(type_icon_results[-1])

    return await template_to_pic(
        template_path=TEMPLATE_PATH,
        template_name="template.html",
        templates={
            "pet_name": pet.name,
            "pet_id": pet.id,
            "pet_gender_id": pet.gender.id,
            "pet_gender_icon": f"images/{pet.gender.id}.png",
            "pet_type_id": pet.type.id,
            "pet_type_name": pet.type.name,
            "pet_head_img": to_data_uri(pet_head_bytes),
            "pet_body_img": to_data_uri(pet_body_bytes),
            "type_icons": type_icons,
            "stats": stats,
            "advance_stats": advance_stats,
            "soulmarks": soulmarks,
            "fifth_skills": fifth_skills[::-1],
            "advanced_skills": advanced_skills[::-1],
            "special_skills": special_skills[::-1],
            "level_skills": level_skills,
        },
        max_width=1200,
        allow_refit=False,
    )
