from typing import Annotated, TypeAlias

from pydantic import AnyHttpUrl, BaseModel, WrapValidator

StrHttpUrl: TypeAlias = Annotated[
    str,
    WrapValidator(lambda v, next_: str(AnyHttpUrl(next_(v)))),
]


class Media(BaseModel):
    pass


class RefMedia(Media):
    url: StrHttpUrl
    headers: dict[str, str] | None = None


class VideoMedia(RefMedia):
    thumbnail_url: StrHttpUrl | None = None


class ImageMedia(RefMedia):
    pass


class AudioMedia(RefMedia):
    pass


class RawMedia(Media):
    content: bytes


__all__ = [
    "Media",
    "RefMedia",
    "AudioMedia",
    "VideoMedia",
    "ImageMedia",
    "RawMedia",
]
