from hishel.httpx import AsyncCacheClient
from httpx import HTTPStatusError
from nonebot.params import Depends
from nonebot_plugin_saa import Image, MessageSegmentFactory, Text

from .parse_arg import parse_string_arg


async def create_image_segment_from_url(url: str) -> Image:
    async with AsyncCacheClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return Image(response.content)


class GetImage:
    def __init__(self, url_template: str) -> None:
        self.url_template = url_template

    async def get(self, arg: str) -> MessageSegmentFactory:
        url = self.url_template.format(arg)
        try:
            return await create_image_segment_from_url(url)
        except HTTPStatusError as e:
            status_code = e.response.status_code
            reason_phrase = e.response.reason_phrase
            return Text(f"❌获取图片失败！原因：{status_code} {reason_phrase}")

    async def __call__(
        self,
        arg: str = Depends(parse_string_arg),
    ) -> MessageSegmentFactory:
        return await self.get(arg)
