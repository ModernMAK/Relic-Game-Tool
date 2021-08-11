import sys
from os.path import splitext
from relic.chunky import RelicChunky
from relic.dumper import dump_chunky


def wait():
    _ = input("\nPress Any Key To Continue...")


# parser = argparse.ArgumentParser("Convert's a Relic Chunky to a collection of files.")

if __name__ == "__main__":
    # sys.argv = ["",
    #             # r"D:\Dumps\DOW_III\full_dump\art\armies\astra_militarum\troops\cadian\armour\varlock_guard_damage_common\varlock_guard_damage_common.rgm"]
    #             r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops\gaurdsman\guardsman.model"]

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
            raise e
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
