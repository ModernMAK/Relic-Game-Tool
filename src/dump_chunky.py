def wait():
    _ = input("\nPress Any Key To Continue...")


import sys
from os.path import splitext

from relic.chunky import RelicChunky
from relic.dumper import dump_chunky

# parser = argparse.ArgumentParser("Convert's a Relic Chunky to a collection of files.")

if __name__ == "__main__":
    sys.argv = ["",r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\heads\general\general_head.model"]
    # Potentially Drag-N-Drop
    if len(sys.argv) == 2:
        try:
            _, file_path = sys.argv
            out_file_path, _ = splitext(file_path)
            print(file_path, "=>", out_file_path)
            with open(file_path, "rb") as handle:
                chunky = RelicChunky.unpack(handle)
                dump_chunky(chunky, out_file_path, include_meta=True)
        except Exception as e:
            print(e)
        wait()
    elif len(sys.argv) > 1:
        print(sys.argv)
        wait()
        pass
    else:
        print("err")
        wait()
        raise NotImplementedError
