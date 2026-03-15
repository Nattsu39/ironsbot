from nonebot.params import Depends

from ironsbot.utils.image import GetImage

PET_IMAGE_URL_TEMPLATE = "https://newseer.61.com/web/monster/body/{}.png"
PetBodyImageGetter = GetImage(PET_IMAGE_URL_TEMPLATE)
PetBodyImage = Depends(PetBodyImageGetter)


MINTMARK_IMAGE_URL_TEMPLATE = "https://newseer.61.com/web/countermark/icon/{}.png"
MintmarkBodyImageGetter = GetImage(MINTMARK_IMAGE_URL_TEMPLATE)
MintmarkBodyImage = Depends(MintmarkBodyImageGetter)


ELEMENT_TYPE_IMAGE_URL_TEMPLATE = "https://newseer.61.com/web/PetType/{}.png"
ElementTypeImageGetter = GetImage(ELEMENT_TYPE_IMAGE_URL_TEMPLATE)
ElementTypeImage = Depends(ElementTypeImageGetter)

PREVIEW_IMAGE_URL_TEMPLATE = "https://cnb.cool/HurryWang/seer-unity-preview-img-dumper-cnb/-/git/raw/master/img/preview.png"
PreviewImageGetter = GetImage(PREVIEW_IMAGE_URL_TEMPLATE)
PreviewImage = Depends(PreviewImageGetter)
