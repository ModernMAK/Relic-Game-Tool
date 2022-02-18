import sys
from os.path import splitext

from relic.chunk_formats.Dow2.model.model_chunky import ModelChunky
from relic.chunk_formats.Dow2.model.writer import dump_model_as_obj
from relic.chunk_formats.Dow3.rgm.rgm_chunky import RgmChunky
from relic.chunk_formats.Dow3.rgm.writer import dump_rgm_as_obj
from relic.chunky import RelicChunky
from relic.chunky.version import RelicChunkyVersion


def wait():
    _ = input("\nPress Any Key To Continue...")


# parser = argparse.ArgumentParser("Convert's a Relic Chunky to a collection of files.")

if __name__ == "__main__":
    # Potentially Drag-N-Drop
    if len(sys.argv) == 2:
        try:
            _, file_path = sys.argv
            file_path: str
            out_file_path, _ = splitext(file_path)
            # HACK to guess texture_root
            # normally models are in an art folder, if it is, we can easily get the root since 'art' is a sub-folder of root
            #   We specifically check for the ART folder by explicitly searching \art\ to avoid cases for \artillery or \game_particles (containing \art and art respectively)
            if "\\art\\" in file_path:
                texture_root_path, _ = file_path.split("\\art\\", 1)
            else:
                raise NotImplementedError()
                # texture_root_path = r"D:\\Dumps\DOW_III\full_dump"  # TODO write a hack or something to calc this

            # TODO make compatible with both DOW 1 & 2
            # Dow 1 keeps the textures in chunkies (RTX/RSH/WTP) ~ These are either TGA or DDS internally
            # Dow 2 keeps the textures in 'loose' files instead of packed into a Chunky ~ These appear to always be DDS
            texture_ext = ".dds"

            print(file_path, "=>", out_file_path)
            with open(file_path, "rb") as handle:
                chunky = RelicChunky.unpack(handle)
                base_path, _ = splitext(file_path)
                obj_path = base_path + ".obj"
                mtl_path = base_path + ".mtl"
                with open(obj_path, "w") as obj_file:
                    with open(mtl_path, "w") as mtl_file:

                        if chunky.header.version == RelicChunkyVersion.v3_1:
                            model = ModelChunky.convert(chunky)
                            dump_model_as_obj(model, mtl_path, obj_file, mtl_file, texture_root_path, texture_ext)
                        elif chunky.header.version == RelicChunkyVersion.v4_1:
                            rgm = RgmChunky.convert(chunky)

                            # offset = 0
                            # for i in range(0, len(rgm.modl.mesh.mgrp.meshes)):
                            #     if i not in [0,1,2]:
                            #         continue
                            #         # break
                            #
                            #     offset += write_rgm_mesh_to_obj(obj_file, rgm, i, offset)

                            dump_rgm_as_obj(rgm, mtl_path, obj_file, mtl_file, texture_root_path, texture_ext)
                        else:
                            raise NotImplementedError(chunky.header.version)
                # dump_chunky(chunky, out_file_path, include_meta=True)
        except Exception as e:
            raise
    elif len(sys.argv) > 1:
        print(sys.argv)
        wait()
        pass
    else:
        print("err")
        wait()
        raise NotImplementedError
