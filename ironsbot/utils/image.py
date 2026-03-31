from hishel.httpx import AsyncCacheClient
from httpx import HTTPStatusError, RequestError
from nonebot.params import Depends
from nonebot_plugin_saa import Image, MessageSegmentFactory, Text

from .parse_arg import parse_string_arg


async def fetch_image_bytes(url: str) -> bytes:
    async with AsyncCacheClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def create_image_segment_from_url(url: str) -> Image:
    return Image(await fetch_image_bytes(url))


class GetImage:
    def __init__(self, *url_templates: str) -> None:
        if not url_templates:
            raise ValueError("至少需要一个 URL 模板")
        self.url_templates = url_templates

    async def get_bytes(self, arg: str) -> bytes:
        """获取图片原始字节，依次尝试所有 URL 模板，全部失败时抛出最后一个异常。"""
        last_error: Exception | None = None
        for template in self.url_templates:
            url = template.format(arg)
            try:
                return await fetch_image_bytes(url)
            except (HTTPStatusError, RequestError) as e:
                last_error = e
                continue
        raise last_error or RuntimeError("所有 URL 均请求失败")

    async def get(self, arg: str) -> MessageSegmentFactory:
        last_error: Exception | None = None
        for template in self.url_templates:
            url = template.format(arg)
            try:
                return await create_image_segment_from_url(url)
            except (HTTPStatusError, RequestError) as e:
                last_error = e
                continue

        if isinstance(last_error, HTTPStatusError):
            code = last_error.response.status_code
            reason = last_error.response.reason_phrase
            return Text(f"❌获取图片失败！原因：{code} {reason}")
        return Text(f"❌获取图片失败！原因：{last_error}")

    async def __call__(
        self,
        arg: str = Depends(parse_string_arg),
    ) -> MessageSegmentFactory:
        if not arg:
            return Text("❌获取图片失败！原因：参数不能为空")

        return await self.get(arg)
