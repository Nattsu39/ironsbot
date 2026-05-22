import httpx
from nonebot.adapters import Message, MessageTemplate
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.typing import T_State

from ironsbot.plugins.get_seer_info.group import matcher_group
from ironsbot.utils.rule import no_reply, startswith_or_endswith
from ironsbot.utils.parse_arg import parse_string_arg

from ..prompt import (
    PROMPT_STATE_KEY,
    Prompt,
    PromptItem,
    create_prompt_got_handler,
)

share_config_matcher = matcher_group.on_message(
    rule=startswith_or_endswith(("配置", "查询配置", "分享配置")) & no_reply()
)

USER_API_BASE = "http://crispww.cn:8081/api"
SEER_API_BASE = "https://crispww.cn/api"

async def search_shares(keyword: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{USER_API_BASE}/shares/search", params={"keyword": keyword, "size": 10})
            resp.raise_for_status()
            data = resp.json()
            return data.get("content", [])
        except Exception as e:
            return []

async def get_config_detail(config_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{SEER_API_BASE}/user-sprites/{config_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return None

def format_config_message(cfg: dict, share_info: dict) -> str:
    msg = f"【分享配置】{cfg.get('spriteName', '未知精灵')}\n"
    msg += f"分享者: {share_info.get('username', '未知')}\n"
    msg += f"标题: {share_info.get('title', '无')}\n"
    msg += "-" * 20 + "\n"
    
    # 属性/能力
    evs = cfg.get("evs", {})
    ev_str = " ".join([f"{k}:{v}" for k, v in evs.items() if v > 0])
    msg += f"学习力: {ev_str if ev_str else '无'}\n"
    msg += f"性格: {cfg.get('personalityName', '无')}\n"
    msg += f"特性: {cfg.get('traitName', '无')} {cfg.get('traitLevel', '')}\n"
    
    # 刻印
    engravings = cfg.get("engravingNames", [])
    eng_str = ", ".join([e for e in engravings if e])
    msg += f"刻印: {eng_str if eng_str else '无'}\n"
    
    # 装备
    equip = []
    if cfg.get("equipmentSuitName"): equip.append(cfg.get("equipmentSuitName"))
    if cfg.get("equipmentGlassesName"): equip.append(cfg.get("equipmentGlassesName"))
    if cfg.get("equipmentWaistName"): equip.append(cfg.get("equipmentWaistName"))
    msg += f"装备: {', '.join(equip) if equip else '无'}\n"
    
    # 技能
    skills = cfg.get("skillGemBindings", [])
    skill_names = [s.get("skillName", "未知") for s in skills if s.get("skillName")]
    msg += f"技能: {', '.join(skill_names) if skill_names else '无'}\n"
    
    return msg

@share_config_matcher.handle()
async def handle_share_config(
    matcher: Matcher,
    state: T_State,
    arg: str = Depends(parse_string_arg)
) -> None:
    if not arg:
        await matcher.finish("请输入要查询的精灵名称，例如：查询配置 盖亚")
        
    shares = await search_shares(arg)
    if not shares:
        await matcher.finish(f"未找到包含“{arg}”的分享配置。")
        
    if len(shares) == 1:
        share = shares[0]
        cfg = await get_config_detail(share["configId"])
        if not cfg:
            await matcher.finish("获取配置详情失败。")
        await matcher.finish(format_config_message(cfg, share))
        
    # Multiple shares
    items = []
    state["shares_map"] = {}
    for share in shares:
        title = share.get("title", "无标题")
        username = share.get("username", "未知")
        config_id = share["configId"]
        items.append(PromptItem(name=title, desc=f"作者: {username}", value=config_id))
        state["shares_map"][config_id] = share
        
    state[PROMPT_STATE_KEY] = Prompt(
        title="找到多条配置，请问你想查询哪一条？",
        items=items,
    )
    state["prompt_message"] = state[PROMPT_STATE_KEY].build_message()

async def share_config_resolver(
    item: PromptItem[str], matcher: Matcher, state: T_State
) -> None:
    config_id = item.value
    share = state.get("shares_map", {}).get(config_id, {})
    cfg = await get_config_detail(config_id)
    if not cfg:
        await matcher.finish("获取配置详情失败。")
    await matcher.finish(format_config_message(cfg, share))

SHARE_CONFIG_GOT_KEY = "share_config"
share_config_matcher.got(SHARE_CONFIG_GOT_KEY, prompt=MessageTemplate("{prompt_message}"))(
    create_prompt_got_handler(SHARE_CONFIG_GOT_KEY, share_config_resolver)
)
