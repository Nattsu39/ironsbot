from httpx import HTTPStatusError
from nonebot.params import Depends

from ironsbot.utils.image import GetImage, fetch_image_bytes


async def _fallback_image(error: Exception) -> bytes:
    if isinstance(error, HTTPStatusError):
        code = error.response.status_code
        reason = error.response.reason_phrase
        text = f"{code} {reason}"
    else:
        text = "获取图片失败！"
    return await fetch_image_bytes(f"https://dummyimage.com/300&text={text}")


PetBodyImageGetter = GetImage(
    "https://newseer.61.com/web/monster/body/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/pet/body/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/pet/body/{}.png",
    fallback=_fallback_image,
)
PetBodyImage = Depends(PetBodyImageGetter)

PetHeadImageGetter = GetImage(
    "https://newseer.61.com/web/monster/head/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/pet/head/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/pet/head/{}.png",
    fallback=_fallback_image,
)
PetHeadImage = Depends(PetHeadImageGetter)

MintmarkBodyImageGetter = GetImage(
    "https://newseer.61.com/web/countermark/icon/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/countermark/icon/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/countermark/icon/{}.png",
)
MintmarkBodyImage = Depends(MintmarkBodyImageGetter)

ElementTypeImageGetter = GetImage(
    "https://newseer.61.com/web/PetType/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/pettype/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/pettype/{}.png",
)
ElementTypeImage = Depends(ElementTypeImageGetter)

PreviewImageGetter = GetImage(
    "https://cnb.cool/HurryWang/seer-unity-preview-img-dumper-cnb/-/git/raw/master/img/preview.png",
)
PreviewImage = Depends(PreviewImageGetter)


AvatarHeadImageGetter = GetImage(
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/avatar/head/{}.png",
)
AvatarHeadImage = Depends(AvatarHeadImageGetter)

AvatarFrameImageGetter = GetImage(
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/avatar/frame/{}.png",
)
AvatarFrameImage = Depends(AvatarFrameImageGetter)

SuitImageGetter = GetImage(
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/item/cloth/suiticon/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/item/cloth/suiticon/{}.png",
)
SuitImage = Depends(SuitImageGetter)

EquipImageGetter = GetImage(
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/item/cloth/prev/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/item/cloth/prev/{}.png",
)
EquipImage = Depends(EquipImageGetter)

TitleImageGetter = GetImage(
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/achieve/title/{}.png",
    "https://raw.githubusercontent.com/SeerAPI/seer-unity-assets/refs/heads/main/newseer/assets/art/ui/assets/achieve/title/{}.png",
)
TitleImage = Depends(TitleImageGetter)
