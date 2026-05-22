from pathlib import Path
from datetime import datetime
from typing import Any, Literal, TypedDict

from nonebot import require
from nonebot_plugin_htmlkit import template_to_pic
from seerapi_models import GlossaryEntryORM, PetORM, SkillInPetORM, SoulmarkORM

from ironsbot.utils.soulmark_parser import SoulmarkDescParser

require(name="nonebot_plugin_htmlkit")

TEMPLATES_PATH = Path(__file__).parent / "templates"
PET_IMAGE_URL = "https://newseer.61.com/web/monster/body/{}.png"
PET_HEAD_IMAGE_URL = "https://newseer.61.com/web/monster/head/{}.png"

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
    effects = [{"id": e.effect_id, "info": e.info} for e in skill.skill_effect]
    skill_activation_item = (
        skill_in_pet.skill_activation_item.name
        if skill_in_pet.skill_activation_item
        else None
    )
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
    desc_parser = SoulmarkDescParser(sm.analyze_desc or sm.desc)
    desc = desc_parser.to_html(
        {
            "#f35555": lambda t: f'<b style="color:#60e0ff">{t}</b>',
        }
    )
    return {
        "desc": desc,
        "intensified": sm.intensified,
        "is_adv": sm.is_adv,
        "pve_effective": sm.pve_effective,
        "tags": tags,
        "glossaries": [{"name": g.name, "desc": g.desc} for g in glossaries],
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

    return await template_to_pic(
        template_path=TEMPLATES_PATH,
        template_name="pet_info.html",
        templates={
            "pet_name": pet.name,
            "pet_id": pet.id,
            "pet_gender_id": pet.gender.id,
            "pet_gender_icon": f"images/{pet.gender.id}.png",
            "pet_type_id": pet.type.id,
            "pet_type_name": pet.type.name,
            "pet_head_url": PET_HEAD_IMAGE_URL.format(pet.resource_id),
            "pet_image_url": PET_IMAGE_URL.format(pet.resource_id),
            "type_icon_url": "https://newseer.61.com/web/PetType/{}.png",
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


async def render_share_config_card(cfg: dict, share_info: dict) -> bytes:
    sprite_name = cfg.get("spriteName") or cfg.get("sprite_name") or "未知精灵"
    share_title = share_info.get("title") or ""
    avatar_url = share_info.get("avatarPath") or share_info.get("avatar_path") or ""

    evs = cfg.get("evs") or {}
    if isinstance(evs, dict):
        ev_pairs = []
        for k, v in evs.items():
            try:
                iv = int(v)
            except Exception:
                continue
            if iv > 0:
                ev_pairs.append(f"{k}:{iv}")
        evs_text = " ".join(ev_pairs) if ev_pairs else "无"
    else:
        evs_text = "无"

    engraving_names = cfg.get("engravingNames") or cfg.get("engraving_names") or []
    if not isinstance(engraving_names, list):
        engraving_names = []
    engraving_names = [str(x) for x in engraving_names if x]

    skills = cfg.get("skillGemBindings") or cfg.get("skill_gem_bindings") or []
    skill_names: list[str] = []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict):
                name = s.get("skillName") or s.get("skill_name")
                if name:
                    skill_names.append(str(name))

    personality_name = cfg.get("personalityName") or cfg.get("personality_name") or "无"
    trait_name = cfg.get("traitName") or cfg.get("trait_name") or "无"
    trait_level = cfg.get("traitLevel") or cfg.get("trait_level") or ""
    if trait_level:
        trait_name = f"{trait_name} {trait_level}"

    equip_suit = cfg.get("equipmentSuitName") or cfg.get("equipment_suit_name") or "无"
    equip_glasses = cfg.get("equipmentGlassesName") or cfg.get("equipment_glasses_name") or "无"
    equip_waist = cfg.get("equipmentWaistName") or cfg.get("equipment_waist_name") or "无"

    return await template_to_pic(
        template_path=TEMPLATES_PATH,
        template_name="share_config.html",
        templates={
            "sprite_name": sprite_name,
            "share_title": share_title,
            "avatar_url": avatar_url,
            "personality_name": personality_name,
            "trait_name": trait_name,
            "evs_text": evs_text,
            "engraving_names": engraving_names,
            "equip_suit": equip_suit,
            "equip_glasses": equip_glasses,
            "equip_waist": equip_waist,
            "skill_names": skill_names,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        max_width=1200,
        allow_refit=False,
    )
