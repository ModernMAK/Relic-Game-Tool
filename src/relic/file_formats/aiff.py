from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Tuple, Union, List, Optional

from serialization_tools.magic import MagicWord
from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct


@dataclass
class Ssnd:
    MAGIC_SSND = MagicWord(Struct("> 4s"), "SSND".encode("ascii"))
    LAYOUT = Struct("> l L L H")  # Relic has an extra short in there
    LEN_OFFSET = 4 + 4 + 2  # +4 (l) + 4 (l) + 2 (h)
    # According to the DOW spec, offset and blocksize is always 0
    SSND_OFFSET = 0
    SSND_BLOCK_SIZE = 0

    data: bytes
    block_bitrate: int

    def write(self, stream: BinaryIO) -> int:
        return self.write_data(stream, self.data, self.block_bitrate)

    @classmethod
    def read(cls, stream: BinaryIO) -> Ssnd:
        args = cls.read_data(stream)
        return cls(*args)

    @classmethod
    def write_data(cls, stream: BinaryIO, data: bytes, block_bitrate: int) -> int:
        written = 0
        written += cls.MAGIC_SSND.write_magic_word(stream)
        size = len(data) + cls.LEN_OFFSET
        now = stream.tell() + 4
        written += cls.LAYOUT.pack_stream(stream, size, cls.SSND_OFFSET, cls.SSND_BLOCK_SIZE, block_bitrate)
        written += stream.write(data)
        assert stream.tell() - now == size, (stream.tell() - now, size)
        return written

    @classmethod
    def read_data(cls, stream: BinaryIO) -> Tuple[bytes, int]:
        cls.MAGIC_SSND.assert_magic_word(stream)
        size, _, _, block_bitrate = cls.LAYOUT.unpack_stream(stream)
        size -= cls.LEN_OFFSET
        data = stream.read(size)
        return data, block_bitrate


@dataclass
class Marker:
    LAYOUT = VStruct("> h L >p x")  # Relic has an extra short in there
    DEFAULT_BEGIN_LOOP = (0x01, 0x00, "beg loop")
    DEFAULT_END_LOOP = (0x02, 0xffffffff, "end loop")
    DEFAULT_START_OFFSET = (0x03, 0x00, "start offset")

    index: int
    position: int
    name: str

    def write(self, stream: BinaryIO) -> int:
        return self.write_data(stream, self.index, self.position, self.name)

    @classmethod
    def read(cls, stream: BinaryIO) -> Marker:
        args = cls.read_data(stream)
        return cls(*args)

    @classmethod
    def read_data(cls, stream: BinaryIO) -> Tuple[int, int, str]:
        index, pos, name = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        return index, pos, name

    @classmethod
    def write_data(cls, stream: BinaryIO, index: int, pos: int, name: str) -> int:
        n = name.encode("ascii")
        return cls.LAYOUT.pack_stream(stream, index, pos, n)

    @classmethod
    def write_defaults(cls, stream: BinaryIO) -> int:
        total = cls.write_data(stream, *cls.DEFAULT_BEGIN_LOOP)
        total += cls.write_data(stream, *cls.DEFAULT_END_LOOP)
        total += cls.write_data(stream, *cls.DEFAULT_START_OFFSET)
        return total

    @classmethod
    def default_begin_loop(cls) -> Marker:
        return cls(*cls.DEFAULT_BEGIN_LOOP)

    @classmethod
    def default_end_loop(cls) -> Marker:
        return cls(*cls.DEFAULT_END_LOOP)

    @classmethod
    def default_start_offset(cls) -> Marker:
        return cls(*cls.DEFAULT_START_OFFSET)

    @classmethod
    def defaults(cls) -> List[Marker]:
        return [cls.default_begin_loop(), cls.default_end_loop(), cls.default_end_loop()]


@dataclass
class Mark:
    MAGIC_MARK = MagicWord(Struct(">4s"), "MARK".encode())
    LAYOUT = Struct(">lh")
    LEN_OFFSET = 2  # The extra short before

    markers: List[Marker]

    def write(self, stream: BinaryIO) -> int:
        with BytesIO() as mark_stream:
            for m in self.markers:
                m.write(mark_stream)
            mark_stream.seek(0)
            buffer = mark_stream.read()
            return self.write_data(stream, len(self.markers), buffer)

    @classmethod
    def read(cls, stream: BinaryIO) -> Mark:
        args = cls.read_data(stream)
        return cls(args)

    @classmethod
    def write_data(cls, stream: BinaryIO, count: int, data: bytes) -> int:
        written = 0
        written += cls.MAGIC_MARK.write_magic_word(stream)
        size = len(data) + cls.LEN_OFFSET
        now = stream.tell() + 4
        written += cls.LAYOUT.pack_stream(stream, size, count)
        written += stream.write(data)
        assert stream.tell() - now == size, (size, stream.tell() - now)
        return written

    @classmethod
    def read_data(cls, stream: BinaryIO) -> List[Marker]:
        cls.MAGIC_MARK.assert_magic_word(stream)
        size, count = cls.LAYOUT.unpack_stream(stream)
        size -= cls.LEN_OFFSET
        buffer = stream.read(size)
        with BytesIO(buffer) as marker_stream:
            markers = [Marker.read(marker_stream) for _ in range(count)]
        return markers

    @classmethod
    def default(cls) -> Mark:
        return cls(Marker.defaults())


@dataclass
class Comm:
    COMM_MAGIC = MagicWord(Struct("> 4s"), "COMM".encode("ascii"))
    # byte size, channels, sample_frames, sample_size, sample_rate, compression 4cc, desc string (byte vlen)
    LAYOUT = VStruct("> l h L h 10s 4s >p >x")  # The most infuriating thing I've ever seen; a pascal string that is null terminated, but the terminal isn't included?
    LEN_SHIFT = LAYOUT.min_size - 4  # -4 for len # INCLUDE PAD IN SIZE

    channels: int
    sample_frames: int
    sample_size: int
    sample_rate: Union[int, bytes]
    compCC: str
    description: str

    RELIC_COMP_4CC = "COMP"
    RELIC_COMP_DESC = "Relic Codec v1.6"
    _FIXED_SAMPLE_RATE = bytes([0x40, 0x0e, 0xac, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    @classmethod
    def relic_default(cls, channels: int, sample_frames, sample_size) -> Comm:
        return Comm(channels, sample_frames, sample_size, cls._FIXED_SAMPLE_RATE, cls.RELIC_COMP_4CC, cls.RELIC_COMP_DESC)

    def write(self, stream: BinaryIO) -> int:
        return self.write_data(stream, self.channels, self.sample_frames, self.sample_size, self.sample_rate, self.compCC, self.description)

    @classmethod
    def read(cls, stream: BinaryIO) -> Comm:
        args = cls.read_data(stream)
        return cls(*args)

    @staticmethod
    def encode_sample_rate(sample_rate: int) -> bytes:
        # https://babbage.cs.qc.cuny.edu/IEEE-754/
        # I'd love to have an algo for this, but it's too much of a pain to do in python
        lookup = {
            # "40 0D 58 88  00 00 00 00  00000000 00000000"
            # "40 0E 58 88 00 00 00 00  00000000 00000000"
            # "40 0E 77 00 00 00 00 00  00000000 00000000"

            # 40 0D 58 88   00 00 00 00  00 00 00 00  00 00 00 00
            22050: bytes([0x40, 0x0d, 0x58, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            # 40 0E 58 88   00 00 00 00  00 00 00 00  00 00 00 00
            44100: bytes([0x40, 0x0e, 0x58, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            # 40 0E 77 00   00 00 00 00  00 00 00 00  00 00 00 00
            48000: bytes([0x40, 0x0e, 0x77, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),

            # FYI, this works, 22050 does not
            54818: bytes([0x40, 0x0e, 0xac, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        }

        if sample_rate in lookup:
            return lookup[sample_rate]
        raise KeyError(sample_rate)

    @classmethod
    def write_data(cls, stream: BinaryIO, channels: int, sample_frames: int, sample_size: int, sample_rate: int, comp: str, desc: str, *, use_fixed: bool = False) -> int:
        written = 0
        written += cls.COMM_MAGIC.write_magic_word(stream)
        size = len(desc) + cls.LEN_SHIFT
        if isinstance(sample_rate, bytes):
            _sample_rate = sample_rate
        else:
            _sample_rate = cls._FIXED_SAMPLE_RATE if use_fixed else cls.encode_sample_rate(sample_rate)
        now = stream.tell() + 4  # ( +1 from pad)
        written += cls.LAYOUT.pack_stream(stream, size, channels, sample_frames, sample_size, _sample_rate, comp.encode("ascii"), desc.encode("ascii"))
        assert stream.tell() - now == size, (stream.tell() - now, size)
        return written

    @classmethod
    def read_data(cls, stream: BinaryIO) -> Tuple[int, int, int, float, str, str]:
        cls.COMM_MAGIC.assert_magic_word(stream)
        now = stream.tell() + 4
        __size, channels, sample_frames, sample_size, sample_rate, comp, desc = cls.LAYOUT.unpack_stream(stream)
        assert stream.tell() - now == __size, (stream.tell() - now, __size)  # -4 to account for size itself
        comp, desc = comp.decode("ascii"), desc.decode("ascii")
        return channels, sample_frames, sample_size, sample_rate, comp, desc


@dataclass
class Fver:
    FVER_MAGIC = MagicWord(Struct("> 4s"), "FVER".encode("ascii"))
    LAYOUT = Struct(">iI")  # TODO VERIFY >v works (since it's alignment is different
    AIFCVersion1 = 2726318400
    CHUNK_SIZE = 4
    # DEFAULT = bytes([0xa2, 0x80, 0x51, 0x40])
    # EMPTY = bytes()
    #
    # data: bytes
    version: int

    def write(self, stream: BinaryIO) -> int:
        return self.write_data(stream, self.version)

    @classmethod
    def read(cls, stream: BinaryIO) -> Fver:
        args = cls.read_data(stream)
        return cls(args)

    @classmethod
    def write_data(cls, stream: BinaryIO, version: int) -> int:
        written = 0
        written += cls.FVER_MAGIC.write_magic_word(stream)
        written += cls.LAYOUT.pack_stream(stream, cls.CHUNK_SIZE, version)
        return written

    @classmethod
    def read_data(cls, stream: BinaryIO) -> int:
        cls.FVER_MAGIC.assert_magic_word(stream)
        chunk_size, version = cls.LAYOUT.unpack_stream(stream)
        assert chunk_size == cls.CHUNK_SIZE
        return version

    @classmethod
    def write_default(cls, stream: BinaryIO) -> int:
        return cls.write_data(stream, cls.version)

    @classmethod
    def default(cls) -> Fver:
        return cls(cls.AIFCVersion1)


@dataclass
class Form:
    FORM_MAGIC = MagicWord(Struct("> 4s"), "FORM".encode("ascii"))
    AIFC_MAGIC = MagicWord(Struct("> 4s"), "AIFC".encode("ascii"))
    SIZE_LAYOUT = Struct("> l")

    fver: Optional[Fver]
    comm: Optional[Comm]
    ssnd: Optional[Ssnd]
    mark: Optional[Mark]

    @classmethod
    def read(cls, stream: BinaryIO) -> Form:
        ssnd = None
        mark = None
        comm = None
        fver = None
        form_buffer = cls.read_data(stream)
        with BytesIO(form_buffer) as form_stream:
            while form_stream.tell() != len(form_buffer):
                if Fver.FVER_MAGIC.check_magic_word(form_stream, False):
                    if fver:
                        raise ValueError
                    fver = Fver.read(form_stream)
                elif Comm.COMM_MAGIC.check_magic_word(form_stream, False):
                    if comm:
                        raise ValueError
                    comm = Comm.read(form_stream)
                elif Ssnd.MAGIC_SSND.check_magic_word(form_stream, False):
                    if ssnd:
                        raise ValueError
                    ssnd = Ssnd.read(form_stream)
                elif Mark.MAGIC_MARK.check_magic_word(form_stream, False):
                    if mark:
                        raise ValueError
                    mark = Mark.read(form_stream)
                else:
                    raise ValueError(form_stream.read(4).decode("ascii"))
        return Form(fver, comm, ssnd, mark)

    def write(self, stream: BinaryIO) -> int:
        with BytesIO() as buffer_stream:
            # No strict ordering required, but this makes the most sense to me
            self.fver.write(buffer_stream)
            self.comm.write(buffer_stream)
            self.ssnd.write(buffer_stream)
            self.mark.write(buffer_stream)
            buffer_stream.seek(0)
            buffer = buffer_stream.read()
            return self.write_data(stream, buffer)

    @classmethod
    def read_data(cls, stream: BinaryIO) -> bytes:
        cls.FORM_MAGIC.assert_magic_word(stream)
        size = cls.SIZE_LAYOUT.unpack_stream(stream)[0]
        cls.AIFC_MAGIC.assert_magic_word(stream)
        size -= cls.AIFC_MAGIC.layout.size  # Size includes magic AIFC
        buffer = stream.read(size)
        assert len(buffer) == size
        return buffer

    @classmethod
    def write_data(cls, stream: BinaryIO, data: bytes) -> int:
        written = 0
        written += cls.FORM_MAGIC.write_magic_word(stream)
        size = len(data) + cls.AIFC_MAGIC.layout.size  # Size includes magic AIFC
        written += cls.SIZE_LAYOUT.pack_stream(stream, size)
        written += cls.AIFC_MAGIC.write_magic_word(stream)
        written += stream.write(data)
        return written

    @classmethod
    def default(cls, comm: Comm = None, ssnd: Ssnd = None) -> Form:
        return cls(Fver.default(), comm, ssnd, Mark.default())


Aiff = Form
