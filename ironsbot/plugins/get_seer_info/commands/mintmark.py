from nonebot.adapters import Bot, MessageTemplate
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory
from seerapi_models import GemCategoryORM, MintmarkClassCategoryORM, MintmarkORM
from seerapi_models.mintmark import AbilityPartORM, UniversalPartORM

from ironsbot.plugins.get_seer_info.depends.db import (
    GemCategoryDataGetter,
    GetGemCategoryData,
)
from ironsbot.utils.rule import no_reply, startswith_or_endswith

from ..depends import (
    GetMintmarkClassData,
    GetMintmarkData,
    MintmarkBodyImageGetter,
    MintmarkDataGetter,
)
from ..group import matcher_group
from ..prompt import (
    PROMPT_STATE_KEY,
    Prompt,
    PromptItem,
    create_prompt_got_handler,
    simple_prompt_resolver,
)

mintmark_matcher = matcher_group.on_message(
    rule=startswith_or_endswith("刻印") & no_reply()
)


PROMPT_MAX_ITEMS = 20


def _deduplicate(mintmarks: list[MintmarkORM]) -> list[MintmarkORM]:
    seen_ids = set()
    result = []
    for mintmark in mintmarks:
        if mintmark.id not in seen_ids:
            result.append(mintmark)
            seen_ids.add(mintmark.id)
    return result


@mintmark_matcher.handle()
async def handle_mintmark(
    matcher: Matcher,
    state: T_State,
    bot: Bot,
    mintmarks: list[MintmarkORM] = GetMintmarkData(),
    classes: list[MintmarkClassCategoryORM] = GetMintmarkClassData(),
) -> None:
    mintmarks += [part.mintmark for c in classes for part in c.mintmark]
    mintmarks = _deduplicate(mintmarks)

    if not mintmarks:
        raise FinishedException

    if len(mintmarks) == 1:
        msg = await build_mintmark_message(mintmarks[0])
        await msg.finish()

    elif len(mintmarks) > PROMPT_MAX_ITEMS:
        await matcher.finish(f"重名超过{PROMPT_MAX_ITEMS}个，请重新检索关键词！")

    prompt = Prompt(
        title="请问你想查询的刻印是……",
        items=[
            PromptItem(name=mintmark.name, desc=str(mintmark.id), value=mintmark.id)
            for mintmark in mintmarks
        ],
    )
    state[PROMPT_STATE_KEY] = prompt
    state["prompt_message"] = await prompt.build_message().build(bot)


def _fmt_attr(label: str, value: float, col_width: int = 8) -> str:
    text = f"-{label}{value}"
    cjk_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    display_len = len(text) + cjk_count
    return text + "\u2007" * max(col_width - display_len, 1)


async def build_mintmark_message(mintmark: MintmarkORM) -> MessageFactory:
    msg = MessageFactory()
    part = mintmark.ability_part or mintmark.skill_part or mintmark.universal_part
    msg += f"【{mintmark.name}】\n"
    image = await MintmarkBodyImageGetter.get(str(mintmark.id))
    msg += image
    msg += f"⭕🆔：{mintmark.id}\n"
    if isinstance(part, UniversalPartORM):
        class_name = part.mintmark_class.name if part.mintmark_class else "无"
        msg += f"⭕系列：{class_name} \n"

    if isinstance(part, AbilityPartORM):
        attr = part.max_attr_value.to_model()
    elif isinstance(part, (UniversalPartORM)):
        attr = part.max_attr_value.to_model()
        if part.extra_attr_value:
            attr = attr + part.extra_attr_value.to_model()
    else:
        return msg + mintmark.desc

    attr = attr.round()
    msg += f"⭕数值：(总和{attr.total})\n"
    msg += (
        f"{_fmt_attr('攻击', attr.atk)}"
        f"{_fmt_attr('防御', attr.def_)}"
        f"{_fmt_attr('速度', attr.spd)}\n"
        f"{_fmt_attr('特攻', attr.sp_atk)}"
        f"{_fmt_attr('特防', attr.sp_def)}"
        f"{_fmt_attr('体力', attr.hp)}"
    )
    return msg


MINTMARK_GOT_KEY = "mintmark"
mintmark_matcher.got(MINTMARK_GOT_KEY, prompt=MessageTemplate("{prompt_message}"))(
    create_prompt_got_handler(
        MINTMARK_GOT_KEY,
        simple_prompt_resolver(MintmarkDataGetter, build_mintmark_message, "刻印"),
    )
)


gem_matcher = matcher_group.on_message(rule=startswith_or_endswith("宝石") & no_reply())


@gem_matcher.handle()
async def handle_gem(
    matcher: Matcher,
    state: T_State,
    bot: Bot,
    categories: list[GemCategoryORM] = GetGemCategoryData(),
) -> None:
    if not categories:
        raise FinishedException

    if len(categories) == 1:
        msg = await build_gem_message(categories[0])
        await msg.finish()

    elif len(categories) > PROMPT_MAX_ITEMS:
        await matcher.finish(f"重名超过{PROMPT_MAX_ITEMS}个，请重新检索关键词！")

    prompt = Prompt(
        title="请问你想查询的宝石是……",
        items=[
            PromptItem(
                name=category.name,
                desc=f"{category.generation_id}代",
                value=category.id,
            )
            for category in categories
        ],
    )
    state[PROMPT_STATE_KEY] = prompt
    state["prompt_message"] = await prompt.build_message().build(bot)


async def build_gem_message(category: GemCategoryORM) -> MessageFactory:
    msg = MessageFactory()
    msg += f"💎以下是{category.name}系列信息：\n"
    gem_info_list = []
    for gem in category.gem:
        effect = " | ".join(f"{effect.info}" for effect in gem.skill_effect_in_use)
        gem_info_list.append(f"【Lv.{gem.level}】 {effect}")
    msg += "\n".join(gem_info_list)
    return msg


GEM_GOT_KEY = "gem"
gem_matcher.got(GEM_GOT_KEY, prompt=MessageTemplate("{prompt_message}"))(
    create_prompt_got_handler(
        GEM_GOT_KEY,
        simple_prompt_resolver(GemCategoryDataGetter, build_gem_message, "宝石"),
    )
)
