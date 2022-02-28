from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from relic.chunky import AbstractChunk, FolderChunk
from relic.chunky.chunk import ChunkType
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.util import find_chunks, find_chunk, UnimplementedFolderChunk, UnimplementedDataChunk


@dataclass
class WhmdChunk(UnimplementedDataChunk):
    pass


@dataclass
class OclrChunk(UnimplementedDataChunk):
    pass


@dataclass
class WclrChunk(UnimplementedDataChunk):
    pass


@dataclass
class HrznChunk(UnimplementedDataChunk):
    pass


@dataclass
class EffcChunk(UnimplementedDataChunk):
    pass


@dataclass
class HmapChunk(UnimplementedDataChunk):
    pass


@dataclass
class TtypChunk(UnimplementedDataChunk):
    pass


@dataclass
class ImapChunk(UnimplementedDataChunk):
    pass


@dataclass
class ChanChunk(AbstractChunk):
    hmap: HmapChunk
    ttyp: TtypChunk
    imap: ImapChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ChanChunk:
        hmap = find_chunk(chunk.chunks, "HMAP", ChunkType.Data)
        hmap = HmapChunk.convert(hmap)

        ttyp = find_chunk(chunk.chunks, "TTYP", ChunkType.Data)
        ttyp = TtypChunk.convert(ttyp)

        imap = find_chunk(chunk.chunks, "IMAP", ChunkType.Data)
        imap = ImapChunk.convert(imap)

        assert len(chunk.chunks) == 3
        return cls(chunk.header, hmap, ttyp, imap)


@dataclass
class VdatChunk(UnimplementedDataChunk):
    pass


@dataclass
class DettChunk(UnimplementedDataChunk):
    pass


@dataclass
class DshdChunk(UnimplementedDataChunk):
    pass


@dataclass
class TfacChunk(AbstractChunk):
    tfac: VdatChunk
    effc: ChanChunk
    hrzn: DettChunk
    decl: DshdChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> TfacChunk:
        vdat = find_chunk(chunk.chunks, "VDAT", ChunkType.Data)
        vdat = VdatChunk.convert(vdat)

        chan = find_chunk(chunk.chunks, "CHAN", ChunkType.Folder)
        chan = ChanChunk.convert(chan)

        dett = find_chunk(chunk.chunks, "DETT", ChunkType.Data)
        dett = DettChunk.convert(dett)

        dshd = find_chunk(chunk.chunks, "DSHD", ChunkType.Data)
        dshd = DshdChunk.convert(dshd)

        assert len(chunk.chunks) == 4
        return cls(chunk.header, vdat, chan, dett, dshd)


@dataclass
class SmapChunk(UnimplementedDataChunk):
    pass


@dataclass
class EntyDataChunk(UnimplementedDataChunk):
    pass


@dataclass
class EntiChunk(UnimplementedDataChunk):
    pass


@dataclass
class EbedChunk(UnimplementedDataChunk):
    pass


@dataclass
class SebdChunk(UnimplementedDataChunk):
    pass


@dataclass
class EntyFolderChunk(AbstractChunk):
    enti: EntiChunk
    ebed: EbedChunk
    sebd: SebdChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> EntyFolderChunk:
        enti = find_chunk(chunk.chunks, "ENTI", ChunkType.Data)
        enti = EntiChunk.convert(enti)

        ebed = find_chunk(chunk.chunks, "EBED", ChunkType.Data)
        ebed = EbedChunk.convert(ebed)

        sebd = find_chunk(chunk.chunks, "SEBD", ChunkType.Data)
        sebd = SebdChunk.convert(sebd)

        assert len(chunk.chunks) == 3
        return cls(chunk.header, enti, ebed, sebd)


@dataclass
class DeclChunk(AbstractChunk):
    smap: SmapChunk
    enty: EntyDataChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> DeclChunk:
        smap = find_chunk(chunk.chunks, "SMAP", ChunkType.Data)
        smap = SmapChunk.convert(smap)

        enty = find_chunk(chunk.chunks, "ENTY", ChunkType.Data)
        enty = EntyDataChunk.convert(enty)

        assert len(chunk.chunks) == 2
        return cls(chunk.header, smap, enty)


@dataclass
class TerrChunk(AbstractChunk):
    tfac: TfacChunk
    effc: EffcChunk
    hrzn: HrznChunk
    decl: DeclChunk
    wclr: WclrChunk
    oclr: OclrChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> TerrChunk:
        tfac = find_chunk(chunk.chunks, "TFAC", ChunkType.Folder)
        tfac = TfacChunk.convert(tfac)

        effc = find_chunk(chunk.chunks, "EFFC", ChunkType.Data)
        effc = EffcChunk.convert(effc)

        hrzn = find_chunk(chunk.chunks, "HRZN", ChunkType.Data)
        hrzn = HrznChunk.convert(hrzn)

        decl = find_chunk(chunk.chunks, "DECL", ChunkType.Folder)
        decl = DeclChunk.convert(decl)

        wclr = find_chunk(chunk.chunks, "WCLR", ChunkType.Data)
        wclr = WclrChunk.convert(wclr)

        oclr = find_chunk(chunk.chunks, "OCLR", ChunkType.Data)
        oclr = OclrChunk.convert(oclr)

        assert len(chunk.chunks) == 6
        return cls(chunk.header, tfac, effc, hrzn, decl, wclr, oclr)


@dataclass
class ImpaChunk(UnimplementedDataChunk):
    pass


@dataclass
class PrmpChunk(UnimplementedDataChunk):
    pass


@dataclass
class PasmChunk(UnimplementedDataChunk):
    pass


@dataclass
class PfdrChunk(AbstractChunk):
    impa: ImpaChunk
    prmp: PrmpChunk
    pasm: PasmChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> PfdrChunk:
        impa = find_chunk(chunk.chunks, "IMPA", ChunkType.Data)
        impa = ImpaChunk.convert(impa)

        prmp = find_chunk(chunk.chunks, "PRMP", ChunkType.Data)
        prmp = PrmpChunk.convert(prmp)

        pasm = find_chunk(chunk.chunks, "PASM", ChunkType.Data)
        pasm = PasmChunk.convert(pasm)

        assert len(chunk.chunks) == 3
        return cls(chunk.header, impa, prmp, pasm)


@dataclass
class MstcChunk(AbstractChunk):
    pfdr: PfdrChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MstcChunk:
        pfdr = find_chunk(chunk.chunks, "PFDR", ChunkType.Folder)
        pfdr = PfdrChunk.convert(pfdr)

        assert len(chunk.chunks) == 1
        return cls(chunk.header, pfdr)


@dataclass
class WstcChunk(AbstractChunk):
    terr: TerrChunk
    mstc: MstcChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> WstcChunk:
        terr = find_chunk(chunk.chunks, "TERR", ChunkType.Folder)
        terr = TerrChunk.convert(terr)

        mstc = find_chunk(chunk.chunks, "MSTC", ChunkType.Folder)
        mstc = MstcChunk.convert(mstc)

        assert len(chunk.chunks) == 2
        return cls(chunk.header, terr, mstc)


@dataclass
class EbptChunk(UnimplementedDataChunk):
    pass


@dataclass
class SbptChunk(UnimplementedDataChunk):
    pass


@dataclass
class EntlChunk(AbstractChunk):
    enty: List[EntyFolderChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> EntlChunk:
        enty = find_chunks(chunk.chunks, "ENTY", ChunkType.Folder)
        enty = [EntyFolderChunk.convert(_) for _ in enty]
        assert len(enty) == len(chunk.chunks)
        return cls(chunk.header, enty)


@dataclass
class SqdiChunk(UnimplementedDataChunk):
    pass


@dataclass
class SqdeChunk(UnimplementedDataChunk):
    pass


@dataclass
class SqddChunk(AbstractChunk):
    sqdi: SqdiChunk
    sqde: SqdeChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SqddChunk:
        sqdi = find_chunk(chunk.chunks, "SQDI", ChunkType.Data)
        sqdi = SqdiChunk.convert(sqdi)

        sqde = find_chunk(chunk.chunks, "SQDE", ChunkType.Data)
        sqde = SqdeChunk.convert(sqde)
        assert len(chunk.chunks) == 2
        return cls(chunk.header, sqdi, sqde)

    pass
    # @classmethod
    # def convert(cls, chunk: FolderChunk) -> SqdlChunk:
    #     assert len(chunk.chunks) == 0, (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])
    #     return cls(chunk.header)


@dataclass
class SqdlChunk(AbstractChunk):
    sqdd: List[SqddChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SqdlChunk:
        sqdd = find_chunks(chunk.chunks, "SQDD", ChunkType.Folder)
        sqdd = [SqddChunk.convert(_) for _ in sqdd]
        assert len(chunk.chunks) == len(sqdd), (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])
        return cls(chunk.header, sqdd)


@dataclass
class PlyrInfoChunk(UnimplementedDataChunk):
    pass


@dataclass
class EgrpChunk(UnimplementedDataChunk):
    pass


@dataclass
class SgrpChunk(UnimplementedDataChunk):
    pass


@dataclass
class PlyrChunk(AbstractChunk):
    info: PlyrInfoChunk
    egrp: EgrpChunk
    sgrp: SgrpChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> PllsChunk:
        info = find_chunk(chunk.chunks, "INFO", ChunkType.Data)
        info = PlyrInfoChunk.convert(info)

        egrp = find_chunk(chunk.chunks, "EGRP", ChunkType.Data)
        egrp = EgrpChunk.convert(egrp)

        sgrp = find_chunk(chunk.chunks, "SGRP", ChunkType.Data)
        sgrp = SgrpChunk.convert(sgrp)

        assert len(chunk.chunks) == 3
        return cls(chunk.header, info, egrp, sgrp)


@dataclass
class PllsChunk(AbstractChunk):
    plyr: List[PlyrChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> PllsChunk:
        plyr = find_chunks(chunk.chunks, "PLYR", ChunkType.Folder)
        plyr = [PlyrChunk.convert(_) for _ in plyr]
        assert len(plyr) == len(chunk.chunks)
        return cls(chunk.header, plyr)


@dataclass
class EgpiChunk(UnimplementedDataChunk):
    pass


@dataclass
class EgrpChunk(UnimplementedDataChunk):
    pass


@dataclass
class EsgpChunk(AbstractChunk):
    egpi: EgpiChunk
    egrp: EgrpChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> EsgpChunk:
        egpi = find_chunk(chunk.chunks, "EGPI", ChunkType.Data)
        egpi = EgpiChunk.convert(egpi)

        egrp = find_chunk(chunk.chunks, "EGRP", ChunkType.Data)
        egrp = EgrpChunk.convert(egrp)

        assert len(chunk.chunks) == 2

        return cls(chunk.header, egpi, egrp)


@dataclass
class EmszChunk(UnimplementedDataChunk):
    pass


@dataclass
class EgmpChunk(AbstractChunk):
    emsz: EmszChunk
    esgp: List[EsgpChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> EgmpChunk:
        emsz = find_chunk(chunk.chunks, "EMSZ", ChunkType.Data)
        emsz = EmszChunk.convert(emsz)
        esgp = find_chunks(chunk.chunks, "ESGP", ChunkType.Folder)
        esgp = [EsgpChunk.convert(_) for _ in esgp]
        assert len(chunk.chunks) == 1 + len(esgp), (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks if _.header.id not in ["EMSZ", "ESGP"]])
        return cls(chunk.header, emsz, esgp)


@dataclass
class GmgrChunk(AbstractChunk):
    egmp: EgmpChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> GmgrChunk:
        egmp = find_chunk(chunk.chunks, "EGMP", ChunkType.Folder)
        egmp = EgmpChunk.convert(egmp)
        assert len(chunk.chunks) == 1
        return cls(chunk.header, egmp)


@dataclass
class SmszChunk(UnimplementedDataChunk):
    pass


@dataclass
class SgpiChunk(UnimplementedDataChunk):
    pass


@dataclass
class SgrpChunk(UnimplementedDataChunk):
    pass


@dataclass
class RoscChunk(UnimplementedDataChunk):
    pass


@dataclass
class SsgpChunk(AbstractChunk):
    sgpi: SgpiChunk
    sgrp: SgrpChunk
    rosc: RoscChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SsgpChunk:
        sgpi = find_chunk(chunk.chunks, "SGPI", ChunkType.Data)
        sgpi = SgpiChunk.convert(sgpi)

        sgrp = find_chunk(chunk.chunks, "SGRP", ChunkType.Data)
        sgrp = SgrpChunk.convert(sgrp)

        rosc = find_chunk(chunk.chunks, "ROSC", ChunkType.Data)
        rosc = RoscChunk.convert(rosc)

        assert len(chunk.chunks) == 3, (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks if _.header.id not in []])
        return cls(chunk.header, sgpi, sgrp, rosc)


@dataclass
class SgmpChunk(AbstractChunk):
    smsz: SmszChunk
    # ssgp: List[SsgpChunk]
    ssgp: Optional[SsgpChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SgmpChunk:
        smsz = find_chunk(chunk.chunks, "SMSZ", ChunkType.Data)
        smsz = SmszChunk.convert(smsz)

        ssgp = find_chunk(chunk.chunks, "SSGP", ChunkType.Folder)
        ssgp = SsgpChunk.convert(ssgp) if ssgp else None
        # ssgp = [SsgpChunk.convert(_) for _ in ssgp]
        assert len(chunk.chunks) == 1 + (1 if ssgp else 0), (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks if _.header.id not in []])
        return cls(chunk.header, smsz, ssgp)


@dataclass
class SgmgChunk(AbstractChunk):
    sgmp: SgmpChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> GmgrChunk:
        sgmp = find_chunk(chunk.chunks, "SGMP", ChunkType.Folder)
        sgmp = SgmpChunk.convert(sgmp)
        assert len(chunk.chunks) == 1
        return cls(chunk.header, sgmp)


@dataclass
class SmkiChunk(UnimplementedDataChunk):
    pass


@dataclass
class SmkdChunk(UnimplementedDataChunk):
    pass


@dataclass
class SmkfChunk(UnimplementedFolderChunk):
    smkd: SmkdChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SmkfChunk:
        smkd = find_chunk(chunk.chunks, "SMKD", ChunkType.Data)
        smkd = SmkiChunk.convert(smkd)
        assert len(chunk.chunks) == 1
        return cls(chunk.header, smkd)


@dataclass
class SmkrChunk(AbstractChunk):
    smki: SmkiChunk
    smkf: SmkfChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SmkrChunk:
        smki = find_chunk(chunk.chunks, "SMKI", ChunkType.Data)
        smki = SmkiChunk.convert(smki)

        smkf = find_chunks(chunk.chunks, "SMKF", ChunkType.Folder)
        smkf = [SmkfChunk.convert(_) for _ in smkf]
        assert len(chunk.chunks) == 1 + len(smkf)
        return cls(chunk.header, smki, smkf)


@dataclass
class ZnmiChunk(UnimplementedDataChunk):
    pass


@dataclass
class ZnesChunk(AbstractChunk):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> ZnesChunk:
        assert len(chunk.chunks) == 0, (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])
        return cls(chunk.header)


@dataclass
class ZnmgChunk(AbstractChunk):
    znmi: ZnmiChunk
    znes: ZnesChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ZnmgChunk:
        znmi = find_chunk(chunk.chunks, "ZNMI", ChunkType.Data)
        znmi = ZnmiChunk.convert(znmi)

        znes = find_chunk(chunk.chunks, "ZNES", ChunkType.Folder)
        znes = ZnesChunk.convert(znes)
        assert len(chunk.chunks) == 2
        return cls(chunk.header, znmi, znes)


@dataclass
class NamDataChunk(UnimplementedDataChunk):
    pass


@dataclass
class TypeChunk(UnimplementedDataChunk):
    pass


@dataclass
class BaseDataChunk(UnimplementedDataChunk):
    pass


@dataclass
class BaseChunk(AbstractChunk):
    data: BaseDataChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> BaseChunk:
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = BaseDataChunk.convert(data)

        assert len(chunk.chunks) == 1
        return cls(chunk.header, data)


@dataclass
class PanmDataChunk(UnimplementedDataChunk):
    pass


@dataclass
class PathDataChunk(UnimplementedDataChunk):
    pass


@dataclass
class FsplChunk(UnimplementedDataChunk):
    pass


@dataclass
class SsplChunk(UnimplementedDataChunk):
    pass


@dataclass
class GsplChunk(UnimplementedDataChunk):
    pass


@dataclass
class PsplChunk(UnimplementedDataChunk):
    pass


@dataclass
class PathChunk(AbstractChunk):
    data: PathDataChunk
    fspl: List[FsplChunk]
    sspl: List[SsplChunk]
    gspl: List[GsplChunk]
    pspl: List[PsplChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> PathChunk:
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = PathDataChunk.convert(data)

        fspl = find_chunks(chunk.chunks, "FSPL", ChunkType.Data)
        fspl = [FsplChunk.convert(_) for _ in fspl]

        sspl = find_chunks(chunk.chunks, "SSPL", ChunkType.Data)
        sspl = [SsplChunk.convert(_) for _ in sspl]

        gspl = find_chunks(chunk.chunks, "GSPL", ChunkType.Data)
        gspl = [GsplChunk.convert(_) for _ in gspl]

        pspl = find_chunks(chunk.chunks, "PSPL", ChunkType.Data)
        pspl = [PsplChunk.convert(_) for _ in pspl]

        assert len(chunk.chunks) == 1 + len(fspl) + len(sspl) + len(gspl) + len(pspl), (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks if _.header.id not in ["DATA", "FSPL", "SSPL", "GSPL", "PSPL"]])
        return cls(chunk.header, data, fspl, sspl, gspl, pspl)


@dataclass
class PanmChunk(AbstractChunk):
    base: BaseChunk
    data: PanmDataChunk
    path: PathChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> CanmChunk:
        base = find_chunk(chunk.chunks, "BASE", ChunkType.Folder)
        base = BaseChunk.convert(base)

        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = PanmDataChunk.convert(data)

        path = find_chunk(chunk.chunks, "PATH", ChunkType.Folder)
        path = PathChunk.convert(path)

        assert len(chunk.chunks) == 3
        return cls(chunk.header, base, data, path)


@dataclass
class CanmChunk(AbstractChunk):
    panm: PanmChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> CanmChunk:
        panm = find_chunk(chunk.chunks, "PANM", ChunkType.Folder)
        panm = PanmChunk.convert(panm)

        assert len(chunk.chunks) == 1
        return cls(chunk.header, panm)


@dataclass
class PdtaChunk(UnimplementedDataChunk):
    pass


@dataclass
class ManmChunk(AbstractChunk):
    panm: PanmChunk
    pdta: PdtaChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> CanmChunk:
        panm = find_chunk(chunk.chunks, "PANM", ChunkType.Folder)
        panm = PanmChunk.convert(panm)

        pdta = find_chunk(chunk.chunks, "PDTA", ChunkType.Data)
        pdta = PdtaChunk.convert(pdta)

        assert len(chunk.chunks) == 2
        return cls(chunk.header, panm, pdta)


@dataclass
class OanmChunk(UnimplementedFolderChunk):
    panm: PanmChunk

    # pdta: PdtaChunk
    #
    @classmethod
    def convert(cls, chunk: FolderChunk) -> CanmChunk:
        panm = find_chunk(chunk.chunks, "PANM", ChunkType.Folder)
        panm = PanmChunk.convert(panm)

        # pdta = find_chunk(chunk.chunks, "PDTA", ChunkType.Data)
        # pdta = PdtaChunk.convert(pdta)

        assert len(chunk.chunks) == 1
        return cls(chunk.header, panm)  # , pdta)


@dataclass
class AnimChunk(AbstractChunk):
    type: TypeChunk
    canm: Optional[CanmChunk]
    manm: Optional[ManmChunk]
    oanm: Optional[OanmChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> AnimChunk:
        type = find_chunk(chunk.chunks, "TYPE", ChunkType.Data)
        type = TypeChunk.convert(type)

        canm = find_chunk(chunk.chunks, "CANM", ChunkType.Folder)
        canm = CanmChunk.convert(canm) if canm else None

        manm = find_chunk(chunk.chunks, "MANM", ChunkType.Folder)
        manm = ManmChunk.convert(manm) if manm else None

        oanm = find_chunk(chunk.chunks, "OANM", ChunkType.Folder)
        oanm = OanmChunk.convert(oanm) if oanm else None

        assert len(chunk.chunks) == 1 + (1 if canm else 0) + (1 if manm else 0) + (1 if oanm else 0), (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])
        return cls(chunk.header, type, canm, manm, oanm)


@dataclass
class AnmsChunk(AbstractChunk):
    anim: List[AnimChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> AnmsChunk:
        anim = find_chunks(chunk.chunks, "ANIM", ChunkType.Folder)
        anim = [AnimChunk.convert(_) for _ in anim]
        assert len(chunk.chunks) == len(anim)
        return cls(chunk.header, anim)


@dataclass
class NamChunk(AbstractChunk):
    data: NamDataChunk
    anms: AnmsChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> NamChunk:
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = NamDataChunk.convert(data)

        anms = find_chunk(chunk.chunks, "ANMS", ChunkType.Folder)
        anms = AnmsChunk.convert(anms)
        assert len(chunk.chunks) == 2
        return cls(chunk.header, data, anms)


@dataclass
class ScarChunk(AbstractChunk):
    gmgr: GmgrChunk
    sgmg: SgmgChunk
    smkr: SmkrChunk
    znmg: ZnmgChunk
    nam: NamChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ScarChunk:
        gmgr = find_chunk(chunk.chunks, "GMGR", ChunkType.Folder)
        gmgr = GmgrChunk.convert(gmgr)

        sgmg = find_chunk(chunk.chunks, "SGMG", ChunkType.Folder)
        sgmg = SgmgChunk.convert(sgmg)

        smkr = find_chunk(chunk.chunks, "SMKR", ChunkType.Folder)
        smkr = SmkrChunk.convert(smkr)

        sqdl = find_chunk(chunk.chunks, "ZNMG", ChunkType.Folder)
        sqdl = ZnmgChunk.convert(sqdl)

        nam = find_chunk(chunk.chunks, "NAM", ChunkType.Folder)
        nam = NamChunk.convert(nam)

        assert len(chunk.chunks) == 5
        return cls(chunk.header, gmgr, sgmg, smkr, sqdl, nam)


@dataclass
class SmegChunk(AbstractChunk):
    ebpt: EbptChunk
    entl: EntlChunk
    sbpt: SbptChunk
    sqdl: SqdlChunk
    plls: PllsChunk
    scar: ScarChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SmegChunk:
        ebpt = find_chunk(chunk.chunks, "EBPT", ChunkType.Data)
        ebpt = EbptChunk.convert(ebpt)

        entl = find_chunk(chunk.chunks, "ENTL", ChunkType.Folder)
        entl = EntlChunk.convert(entl)

        sbpt = find_chunk(chunk.chunks, "SBPT", ChunkType.Data)
        sbpt = SbptChunk.convert(sbpt)

        sqdl = find_chunk(chunk.chunks, "SQDL", ChunkType.Folder)
        sqdl = SqdlChunk.convert(sqdl)

        plls = find_chunk(chunk.chunks, "PLLS", ChunkType.Folder)
        plls = PllsChunk.convert(plls)

        scar = find_chunk(chunk.chunks, "SCAR", ChunkType.Folder)
        scar = ScarChunk.convert(scar)

        assert len(chunk.chunks) == 6
        return cls(chunk.header, ebpt, entl, sbpt, sqdl, plls, scar)


@dataclass
class EinfChunk(UnimplementedDataChunk):
    pass


@dataclass
class MecfChunk(AbstractChunk):
    einf: EinfChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MecfChunk:
        einf = find_chunk(chunk.chunks, "EINF", ChunkType.Data)
        einf = EinfChunk.convert(einf)

        assert len(chunk.chunks) == 1
        return cls(chunk.header, einf)


@dataclass
class ScenChunk(AbstractChunk):
    whmd: WhmdChunk
    wstc: WstcChunk
    smeg: SmegChunk
    mecf: MecfChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ScenChunk:
        whmd = find_chunk(chunk.chunks, "WMHD", ChunkType.Data)
        whmd = WhmdChunk.convert(whmd)

        wstc = find_chunk(chunk.chunks, "WSTC", ChunkType.Folder)
        wstc = WstcChunk.convert(wstc)

        smeg = find_chunk(chunk.chunks, "SMEG", ChunkType.Folder)
        smeg = SmegChunk.convert(smeg)

        mecf = find_chunk(chunk.chunks, "MECF", ChunkType.Folder)
        mecf = MecfChunk.convert(mecf)

        assert len(chunk.chunks) == 4
        return cls(chunk.header, whmd, wstc, smeg, mecf)


@dataclass
class SgbChunky(RelicChunky):
    scen: ScenChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> SgbChunky:
        scen = find_chunk(chunky.chunks, "SCEN", ChunkType.Folder)
        scen = ScenChunk.convert(scen)
        return cls(chunky.header, scen)
