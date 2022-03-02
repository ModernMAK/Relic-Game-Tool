from dataclasses import dataclass
from os.path import basename, splitext
from pathlib import Path
from typing import List, BinaryIO

from relic.chunky.chunk import FolderChunk, ChunkType, AbstractChunk
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.dow.common_chunks.imag import TxtrChunk
from relic.chunky_formats.dow.common_chunks.imag_writer import ImagConverter
from relic.chunky_formats.util import find_chunks, find_chunk


@dataclass
class ShrfChunk(AbstractChunk):
    texture: List[TxtrChunk]
    shdr: FolderChunk  # Shdr Chunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ShrfChunk':
        txtr = find_chunks(chunk.chunks, "TXTR", ChunkType.Folder)
        txtr = [TxtrChunk.convert(_) for _ in txtr]
        shdr = find_chunk(chunk.chunks, "SHDR", ChunkType.Folder)

        # shdr = ShdrChunk.create(shdr_chunk)
        assert len(chunk.chunks) == 1 + len(txtr), ([(c.header.type.name, c.header.id) for c in chunk.chunks])
        return ShrfChunk(chunk.header, txtr, shdr)


@dataclass
class RshChunky(RelicChunky):
    shrf: ShrfChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> 'RshChunky':
        shrf = find_chunk(chunky.chunks, "SHRF", ChunkType.Folder)
        shrf = ShrfChunk.create(shrf)
        assert len(chunky.chunks) == 1
        return RshChunky(chunky.header, shrf)


def write_shrf_txtr(stream: BinaryIO, chunk: TxtrChunk, out_format: str = None, texconv_path: str = None):
    ImagConverter.Imag2Stream(chunk.imag, stream, out_format, texconv_path=texconv_path)


# def write_shrf_textures(root: str, txtr: List[TxtrChunk], out_format: str = None, texconv_path: str = None):
#     p = Path(root)
#     for txtr in txtr:
#         f = p / (str(basename(txtr.header.name)) + ("." + out_format if out_format else ""))
#         with open(f, "wb") as handle:
#             write_shrf_txtr(handle, txtr, out_format, texconv_path)


def write_txtr_list(outpath_path: str, textures: List[TxtrChunk], out_format: str = None, texconv_path: str = None):
    p = Path(outpath_path)
    p.mkdir(parents=True, exist_ok=True)
    for txtr in textures:
        name = basename(txtr.header.name)
        name, x = splitext(name)
        if out_format:
            x = "." + out_format if (out_format[0] != ".") else out_format
        elif not x:
            x = txtr.imag.attr.image_format.extension
        name += x

        with open(p / name, "wb") as handle:
            write_shrf_txtr(handle, txtr, out_format, texconv_path)


def write_txtr(outpath_path: str, texture: TxtrChunk, out_format: str = None, texconv_path: str = None):
    p = Path(outpath_path).parent
    p.mkdir(parents=True, exist_ok=True)
    name = basename(texture.header.name)
    name, x = splitext(name)
    if out_format:
        x = "." + out_format if (out_format[0] != ".") else out_format
    elif not x:
        x = texture.imag.attr.image_format.extension
    name += x
    with open(p / name, "wb") as handle:
        write_shrf_txtr(handle, texture, out_format, texconv_path)


def write_rsh(output_path: str, rsh: RshChunky, out_format: str = None, texconv_path: str = None):
    if len(rsh.shrf.texture) == 1:
        write_txtr(output_path, rsh.shrf.texture[0], out_format, texconv_path)
    else:
        write_txtr_list(output_path, rsh.shrf.texture, out_format, texconv_path)
