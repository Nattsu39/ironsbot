from hishel.httpx import AsyncCacheClient
from httpx import HTTPStatusError, RequestError
from nonebot.params import Depends
from nonebot_plugin_saa import Image, MessageSegmentFactory, Text

from .parse_arg import parse_string_arg


async def create_image_segment_from_url(url: str) -> Image:
    async with AsyncCacheClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return Image(response.content)


class GetImage:
    def __init__(self, *url_templates: str) -> None:
        if not url_templates:
            raise ValueError("至少需要一个 URL 模板")
        self.url_templates = url_templates

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
