from nonebot.adapters import Bot, MessageTemplate
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.typing import T_State
from nonebot_plugin_saa import Image, MessageFactory
from seerapi_models import PetORM, PetSkinORM

from ironsbot.plugins.get_seer_info.group import matcher_group
from ironsbot.utils.rule import no_reply, startswith_or_endswith

from ..depends import GetPetData, GetPetSkinData, PetBodyImageGetter, PetDataGetter
from ..prompt import (
    PROMPT_STATE_KEY,
    Prompt,
    PromptItem,
    create_prompt_got_handler,
    simple_prompt_resolver,
)
from ..render import render_pet_info

pet_image_matcher = matcher_group.on_message(
    rule=startswith_or_endswith(("立绘", "皮肤", "查询立绘")) & no_reply()
)


PROMPT_MAX_ITEMS = 20


@pet_image_matcher.handle()
async def handle_pet_image(
    matcher: Matcher,
    state: T_State,
    bot: Bot,
    pets: list[PetORM] = GetPetData(),
    skins: list[PetSkinORM] = GetPetSkinData(),
) -> None:
    _name_set: set[str] = set()
    items: list[PromptItem[int]] = [
        PromptItem(name=pet.name, desc=str(pet.id), value=pet.id) for pet in pets
    ]
    items.extend(
        PromptItem(
            name=skin.name, desc=f"所属精灵：{skin.pet.name}", value=skin.resource_id
        )
        for skin in skins
    )

    if not items:
        raise FinishedException

    if len(items) == 1:
        msg = await build_pet_image_message(items[0])
        await msg.finish()

    if len(pets) > PROMPT_MAX_ITEMS:
        await matcher.finish(f"重名超过{PROMPT_MAX_ITEMS}个，请重新检索关键词！")

    prompt = Prompt(
        title="请问你想查询的立绘是……",
        items=items,
    )
    state[PROMPT_STATE_KEY] = prompt
    state["prompt_message"] = await prompt.build_message().build(bot)


async def build_pet_image_message(args: PromptItem[int]) -> MessageFactory:
    image = await PetBodyImageGetter.get(str(args.value))
    msg = MessageFactory()
    msg += f"💎{args.name}\n"
    msg += image
    return msg


async def pet_image_resolver(item: PromptItem[int], _1: Matcher, _2: object) -> None:
    msg = await build_pet_image_message(item)
    await msg.finish()


PET_IMAGE_GOT_KEY = "pet_image"
pet_image_matcher.got(PET_IMAGE_GOT_KEY, prompt=MessageTemplate("{prompt_message}"))(
    create_prompt_got_handler(PET_IMAGE_GOT_KEY, pet_image_resolver)
)


# ============ 精灵信息卡 ============

pet_info_matcher = matcher_group.on_message(
    rule=startswith_or_endswith(("精灵", "查询精灵信息", "魂印", "技能")) & no_reply()
)


@pet_info_matcher.handle()
async def handle_pet_info(
    matcher: Matcher,
    state: T_State,
    bot: Bot,
    pets: list[PetORM] = GetPetData(),
    # aliases: list[PetORM] = GetPetData(),
) -> None:
    if not pets:
        raise FinishedException

    if len(pets) == 1:
        msg = await build_pet_info_message(pets[0])
        await msg.finish()

    if len(pets) > PROMPT_MAX_ITEMS:
        await matcher.finish(f"重名超过{PROMPT_MAX_ITEMS}个，请重新检索关键词！")

    prompt = Prompt(
        title="请问你想查询的精灵是……",
        items=[
            PromptItem(name=pet.name, desc=str(pet.id), value=pet.id) for pet in pets
        ],
    )
    state[PROMPT_STATE_KEY] = prompt
    state["prompt_message"] = await prompt.build_message().build(bot)


async def build_pet_info_message(pet: PetORM) -> MessageFactory:
    pic_bytes = await render_pet_info(pet)
    msg = MessageFactory()
    msg += Image(pic_bytes)
    return msg


PET_INFO_GOT_KEY = "pet_info"
pet_info_matcher.got(PET_INFO_GOT_KEY, prompt=MessageTemplate("{prompt_message}"))(
    create_prompt_got_handler(
        PET_INFO_GOT_KEY,
        simple_prompt_resolver(PetDataGetter, build_pet_info_message, "精灵"),
    )
)
