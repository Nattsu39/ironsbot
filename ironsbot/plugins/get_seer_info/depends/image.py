from nonebot.params import Depends

from ironsbot.utils.image import GetImage

PetBodyImageGetter = GetImage(
    "https://newseer.61.com/web/monster/body/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/pet/body/{}.png",
)
PetBodyImage = Depends(PetBodyImageGetter)

PetHeadImageGetter = GetImage(
    "https://newseer.61.com/web/monster/head/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/pet/head/{}.png",
)
PetHeadImage = Depends(PetHeadImageGetter)

MintmarkBodyImageGetter = GetImage(
    "https://newseer.61.com/web/countermark/icon/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/countermark/icon/{}.png",
)
MintmarkBodyImage = Depends(MintmarkBodyImageGetter)

ElementTypeImageGetter = GetImage(
    "https://newseer.61.com/web/PetType/{}.png",
    "https://cnb.cool/SeerAPI/seer-unity-assets/-/git/raw/main/newseer/assets/art/ui/assets/pettype/{}.png",
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
