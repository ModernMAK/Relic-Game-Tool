# TMP's are ???
import zlib
from os.path import splitext

if __name__ == "__main__":
    f = r"???"
    d, _ = splitext(f)
    with open(f, "rb") as infile:
        with open(d + ".bin", "wb") as outfile:
            outfile.write(zlib.decompress(infile.read()))
