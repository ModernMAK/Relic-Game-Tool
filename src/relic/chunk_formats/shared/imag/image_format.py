from enum import Enum


class ImageFormat(Enum):
    TGA = 0

    DXT1 = 8
    DXT3 = 10
    DXT5 = 11

    _ignore_ = ['_extensions', '_dds', '_tga']
    _extensions = {TGA: ".tga", DXT1: ".dds", DXT3: ".dds", DXT5: ".dds"}
    _fourCC = {DXT1: "DXT1", DXT3: "DXT3", DXT5: "DXT5"}  # Decouples the enum name from logic
    _dds = [DXT1, DXT3, DXT5]
    _tga = [TGA]

    @property
    def extension(self) -> str:
        return self._extensions[self.value]

    @property
    def fourCC(self) -> str:
        return self._fourCC[self.value]

    @property
    def is_dxt(self) -> bool:
        return self.value in self._dds

    @property
    def is_tga(self) -> bool:
        return self.value in self._tga
