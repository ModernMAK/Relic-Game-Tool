from dataclasses import dataclass
from typing import List, Optional

from relic.chunk_formats.Dow.shared.imag import ImagChunk
from relic.chunk_formats.Dow.wtp.info_chunk import WtpInfoChunk
from relic.chunk_formats.Dow.wtp.ptbd_chunk import PtbdChunk
from relic.chunk_formats.Dow.wtp.ptbn_chuck import PtbnChunk
from relic.chunk_formats.Dow.wtp.ptld_chunk import PtldChunk
from relic.chunky import FolderChunk


@dataclass
class TpatChunk:
    info: WtpInfoChunk
    imag: ImagChunk

    # New assumption;
    ptld: Optional[List[PtldChunk]] = None
    ptbd: Optional[List[PtbdChunk]] = None
    ptbn: Optional[List[PtbnChunk]] = None

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'TpatChunk':
        info_chunk = chunk.get_chunk(id="INFO")
        imag_chunk = chunk.get_chunk(id="IMAG")
        ptld_chunks = chunk.get_chunk_list(id="PTLD", optional=True)
        ptbd_chunks = chunk.get_chunk_list(id="PTBD", optional=True)
        ptbn_chunks = chunk.get_chunk_list(id="PTBN", optional=True)

        info = WtpInfoChunk.create(info_chunk)
        imag = ImagChunk.convert(imag_chunk)

        ptld = [PtldChunk.create(c) for c in ptld_chunks] if ptld_chunks else None
        ptbd = [PtbdChunk.create(c) for c in ptbd_chunks] if ptbd_chunks else None
        ptbn = [PtbnChunk.create(c) for c in ptbn_chunks] if ptbn_chunks else None

        return TpatChunk(info, imag, ptld, ptbd, ptbn)