from os.path import split, join, abspath


def _find_tests_root_folder() -> str:
    full = __file__
    # should catch my most common test folder name cases
    for _ in range(len(__file__)):
        parent, self = split(full)
        if parent == "" and self == "":
            raise FileNotFoundError("Could not find test root folder!")
        elif self.lower() in ["tests", "test"]:
            return full
        else:
            full = parent
    raise FileNotFoundError("Could not find test root folder! The Process timed out!")


def get_testdata_root_folder() -> str:
    tests_root = _find_tests_root_folder()
    return abspath(join(tests_root, "..", "sample_data"))


def get_testdata_path(relative_path: str):
    if relative_path[0] in ["\\", "/"]:
        relative_path = relative_path[1:]
    return join(get_testdata_root_folder(), relative_path)

lorem_ipsum = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua." \
                  " Malesuada fames ac turpis egestas. Accumsan lacus vel facilisis volutpat est velit." \
                  " Turpis egestas pretium aenean pharetra magna ac placerat vestibulum lectus. Tellus cras adipiscing enim eu turpis egestas." \
                  " Pellentesque adipiscing commodo elit at imperdiet dui accumsan sit. Massa enim nec dui nunc mattis." \
                  " Gravida in fermentum et sollicitudin ac orci phasellus egestas." \
                  " Eu volutpat odio facilisis mauris sit amet massa vitae. Diam quis enim lobortis scelerisque fermentum dui faucibus."
