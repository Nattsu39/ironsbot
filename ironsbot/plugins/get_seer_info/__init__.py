import importlib

from nonebot.plugin import PluginMetadata

from .config import Config

importlib.import_module("ironsbot.plugins.get_seer_info.commands")

usage = """🤖赛尔号数据查询插件，所有命令需放置在消息开头或结尾才能触发，命令和参数间可不添加空格。
💡注意：回复他人消息时不会触发命令。
支持名称模糊搜索和 ID 精确查找，若有多个匹配结果将提示选择。
（🔍名称搜索时可省略 · - 等符号，不区分大小写）

命令：
  🐱精灵相关：
    精灵/查询精灵信息/魂印/技能 <名称/ID>  — 查询精灵基础信息
    > 精灵雷伊
    > 奥菲魂印
    > 圣武技能

    立绘/查询立绘/皮肤 <名称/ID>  — 查询精灵或皮肤立绘
    > 雷伊立绘
    > 雷伊皮肤

  💮刻印相关：
    刻印 <名称/ID>  — 查询刻印信息及数值，支持刻印系列名称搜索
    > 刻印v8
    > 刻印精灵王

    宝石 <名称/ID>  — 查询刻印宝石信息，支持宝石系列名称搜索
    > 冻伤宝石
    > 宝石绝命

  🔀其他：
    下周预告 — 获取下周预告图
    数据版本 — 获取数据更新时间
    开服查询 — 查询服务器是否已开服"""

__plugin_meta__ = PluginMetadata(
    name="赛尔号信息查询",
    description="赛尔号信息查询插件",
    usage=usage,
    config=Config,
    supported_adapters={"~onebot.v11"},
)
