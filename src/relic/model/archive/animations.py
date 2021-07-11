import json
import os
import struct
from dataclasses import dataclass
from io import BytesIO, FileIO
from os.path import join, splitext, dirname
from typing import BinaryIO, List, TextIO

from relic.model.archive import chunky


def raw_dump():
    chunky.dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whe-chunky", [".whe"])

if __name__ == "__main__":
    raw_dump()