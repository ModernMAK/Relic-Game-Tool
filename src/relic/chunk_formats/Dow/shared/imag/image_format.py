from enum import Enum


class ImageFormat(Enum):
    TGA = 0

    DXT1 = 8
    DXT3 = 10
    DXT5 = 11

    @property
    def extension(self) -> str:
        _extensions = {
            ImageFormat.TGA: ".tga",
            ImageFormat.DXT1: ".dds",
            ImageFormat.DXT3: ".dds",
            ImageFormat.DXT5: ".dds"
        }
        return _extensions[self.value]

    @property
    def fourCC(self) -> str:
        _fourCC = {
            ImageFormat.DXT1: "DXT1",
            ImageFormat.DXT3: "DXT3",
            ImageFormat.DXT5: "DXT5"
        }
        return _fourCC[self.value]

    @property
    def is_dxt(self) -> bool:
        _dds = [ImageFormat.DXT1, ImageFormat.DXT3, ImageFormat.DXT5]
        return self.value in _dds

    @property
    def is_tga(self) -> bool:
        _tga = [ImageFormat.TGA]
        return self.value in _tga
